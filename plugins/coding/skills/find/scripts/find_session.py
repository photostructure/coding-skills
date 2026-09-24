#!/usr/bin/env python3
"""Find the local agent session that wrote a change still uncommitted in git.

The target is a changed file, or a snippet of changed text. The script reads
the local transcripts of both supported agent CLIs, keeps every successful
write to the target file, and ranks sessions by how many of the target's
changed lines (against HEAD) those writes added or removed.

- Claude Code: $CLAUDE_CONFIG_DIR/projects (default ~/.claude/projects). A
  successful Edit or Write is a `user` record whose `toolUseResult` carries
  `filePath` plus a `structuredPatch` or, for a new file, `content`. Subagent
  transcripts live under <session>/subagents/ and resume through the parent.
- Codex: $CODEX_HOME/sessions and archived_sessions (default ~/.codex). A
  write is an `item_completed` FileChange item keyed by absolute path, or an
  apply_patch envelope ("*** Begin Patch") inside a tool call whose output
  does not report failure. Code-mode sessions pipe the envelope into an
  interactive `apply_patch` process, which leaves no FileChange item. Guardian
  subagents only assess approval requests and are skipped; spawned subagents
  resume through the parent thread.

A shell command that writes the file (in-place sed or perl, a redirect, tee, a
script that writes) is weaker evidence: a changed line counts when its text
appears in the command. The command must name the file's absolute path, or name
the file while running inside the file's checkout.

A write to a path that no longer exists counts toward a target with the same
file name when that path lies inside the target's checkout and outside its
git-ignored directories: the file was moved or renamed after that write.

A session whose first prompt starts by running the coding review skill is a
reviewer, as are the sessions a cross-model second opinion launches. Reviewers
rank after every author.
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import shlex
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


COMMENT_PREFIX_RE = re.compile(r"^(?:/\*+|\*+/?|//+|#+|--|;+|<!--)\s*")
WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")
REVIEW_PROMPT_RE = re.compile(
    r"\s*(?:<command-message>[^<]*</command-message>\s*)?(?:<command-name>)?"
    r"[/$]coding:review(?:-staged)?(?![\w-])"
)
# Shell edits that do not name the file they write.
SHELL_EDIT_RES = (
    re.compile(r"\bsed\b[^|;&\n]*\s-(?:[a-zA-Z]*i|-in-place)"),
    re.compile(r"\bperl\b[^|;&\n]*\s-[a-zA-Z]*i"),
    re.compile(r"\b(?:python3?|node|ruby)\b[\s\S]*\bwrite"),
    re.compile(r"\b(?:apply_patch|git\s+apply)\b"),
)
# A shorter changed line could appear in an unrelated shell command by chance.
MIN_SHELL_LINE = 8
MAX_UNTRACKED_BYTES = 1 << 20
PATCH_RE = re.compile(r"\*\*\* Begin Patch(.*?)\*\*\* End Patch", re.DOTALL)
PATCH_FILE_RE = re.compile(r"\*\*\* (?:Add|Update|Delete) File: (.+)")
PATCH_MOVE = "*** Move to: "
ESCAPE_RE = re.compile(r"\\(u[0-9a-fA-F]{4}|.)")
ESCAPES = {"n": "\n", "t": "\t", "r": "\r"}
FAILED_EXIT_RE = re.compile(r'"exit_code":\s*[1-9]')
# Older transcripts report a failed patch only in the tool's plain-text output.
PATCH_FAILURE_RE = re.compile(r"apply_patch verification failed|patch rejected|Failed to find expected lines")
CALL_ID_RE = re.compile(rb'"call_id":"([^"]+)"')


@dataclass
class Target:
    path: str
    repo: str
    added: Counter[str]
    removed: Counter[str]


@dataclass
class Write:
    path: str
    at: float
    added: Counter[str] = field(default_factory=Counter)
    removed: Counter[str] = field(default_factory=Counter)
    shell_text: str | None = None


@dataclass
class Session:
    host: str
    session_id: str
    cwd: str | None = None
    title: str | None = None
    first_prompt: str | None = None
    via_subagent: bool = False
    archived: bool = False
    writes: list[Write] = field(default_factory=list)


@dataclass
class Candidate:
    session: Session
    reviewer: bool
    matched: int
    total: int
    shell_only: int
    last_write: Write


def normalize(line: str) -> str:
    text = COMMENT_PREFIX_RE.sub("", line.strip())
    return WHITESPACE_RE.sub(" ", text).strip()


def significant(text: str) -> bool:
    return len(text) >= 4 and any(char.isalnum() for char in text)


def normalized_counts(lines: list[str]) -> Counter[str]:
    return Counter(text for text in map(normalize, lines) if significant(text))


def realpath(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))


def parse_time(stamp: str) -> float:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def git(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def diff_path(raw: str, prefix: str) -> str | None:
    # Git appends a tab to a ---/+++ path that contains a space.
    raw = raw.rstrip("\t")
    if raw == "/dev/null":
        return None
    if raw.startswith('"'):
        raw = codecs.escape_decode(raw[1:-1].encode("utf-8"))[0].decode("utf-8")
    return raw[len(prefix) :]


def read_changes(repo: str, pathspec: list[str]) -> dict[str, tuple[list[str], list[str]]]:
    """Map each changed file's real path to its (added, removed) lines vs HEAD."""
    out = git(
        repo,
        "-c",
        "core.quotePath=false",
        "diff",
        "HEAD",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "-U0",
        "--",
        *pathspec,
    )
    changes: dict[str, tuple[list[str], list[str]]] = {}
    current: tuple[list[str], list[str]] | None = None
    old_path: str | None = None
    for line in out.splitlines():
        if line.startswith("diff --git "):
            current = None
            old_path = None
        elif current is None:
            if line.startswith("--- "):
                old_path = diff_path(line[4:], "a/")
            elif line.startswith("+++ "):
                relative = diff_path(line[4:], "b/") or old_path
                if relative is None:
                    raise SystemExit(f"cannot parse git diff header: {line!r}")
                current = changes.setdefault(realpath(os.path.join(repo, relative)), ([], []))
        elif line.startswith("+"):
            current[0].append(line[1:])
        elif line.startswith("-"):
            current[1].append(line[1:])

    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *pathspec)
    for relative in filter(None, untracked.split("\0")):
        path = os.path.join(repo, relative)
        data = Path(path).read_bytes()
        if len(data) > MAX_UNTRACKED_BYTES or b"\0" in data:
            continue
        changes[realpath(path)] = (data.decode("utf-8", errors="replace").splitlines(), [])
    return changes


def snippet_lines(lines: list[str], snippet: str) -> set[int]:
    """Indexes of the lines that an occurrence of the normalized snippet spans."""
    joined = ""
    spans: list[tuple[int, int, int]] = []
    for index, line in enumerate(lines):
        text = normalize(line)
        if not text:
            continue
        if joined:
            joined += " "
        spans.append((index, len(joined), len(joined) + len(text)))
        joined += text
    hits: set[int] = set()
    begin = joined.find(snippet)
    while begin >= 0:
        end = begin + len(snippet)
        hits.update(index for index, start, stop in spans if start < end and stop > begin)
        begin = joined.find(snippet, begin + 1)
    return hits


def file_target(argument: str, repo: str, path: str, added: list[str], removed: list[str]) -> dict[str, Target]:
    target = Target(path, repo, normalized_counts(added), normalized_counts(removed))
    if not target.added and not target.removed:
        raise SystemExit(f"{argument} changes only blank or punctuation lines")
    return {path: target}


def resolve_targets(argument: str) -> tuple[dict[str, Target], str]:
    """Return the changed lines to attribute, and "file" or "snippet"."""
    path = Path(argument).expanduser()
    if path.is_file():
        repo = git(str(path.resolve().parent), "rev-parse", "--show-toplevel").strip()
        changes = read_changes(repo, [str(path.resolve())])
        if not changes:
            raise SystemExit(f"{argument} has no uncommitted changes against HEAD")
        ((changed_path, (added, removed)),) = changes.items()
        return file_target(argument, repo, changed_path, added, removed), "file"

    repo = git(os.getcwd(), "rev-parse", "--show-toplevel").strip()
    changes = read_changes(repo, [])
    deleted = realpath(argument)
    if deleted in changes:
        return file_target(argument, repo, deleted, *changes[deleted]), "file"

    snippet = " ".join(filter(None, map(normalize, argument.splitlines())))
    targets: dict[str, Target] = {}
    for target_path, (added, removed) in changes.items():
        target = Target(
            target_path,
            repo,
            normalized_counts([added[index] for index in snippet_lines(added, snippet)]),
            normalized_counts([removed[index] for index in snippet_lines(removed, snippet)]),
        )
        if target.added or target.removed:
            targets[target_path] = target
    if not targets:
        raise SystemExit(
            f"no changed line in {repo} (against HEAD, untracked files included) "
            f"contains the snippet: {snippet!r}"
        )
    return targets, "snippet"


@lru_cache(maxsize=None)
def inside_checkout(repo: str, path: str) -> bool:
    """Whether path lies in repo's own working tree, outside ignored directories.

    Ignored directories hold build output and nested agent worktrees, which
    are other checkouts even though they sit inside this one.
    """
    if not path.startswith(repo + os.sep):
        return False
    result = subprocess.run(["git", "-C", repo, "check-ignore", "-q", path], check=False)
    if result.returncode not in (0, 1):
        raise SystemExit(f"git check-ignore failed for {path}")
    return result.returncode == 1


def find_target(targets: dict[str, Target], written: str) -> Target | None:
    real = realpath(written)
    target = targets.get(real)
    if target is not None or os.path.exists(real):
        return target
    # The file may have moved within its checkout since this write.
    name = os.path.basename(real)
    moved = [
        target
        for target in targets.values()
        if os.path.basename(target.path) == name and inside_checkout(target.repo, real)
    ]
    return moved[0] if len(moved) == 1 else None


def patch_lines(lines: list[str]) -> tuple[Counter[str], Counter[str]]:
    """Split hunk lines (no ---/+++ file headers) into added and removed sets."""
    added = [line[1:] for line in lines if line.startswith("+")]
    removed = [line[1:] for line in lines if line.startswith("-")]
    return normalized_counts(added), normalized_counts(removed)


def unescape(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        code = match.group(1)
        return chr(int(code[1:], 16)) if len(code) == 5 else ESCAPES.get(code, code)

    return ESCAPE_RE.sub(replace, text)


def envelope_writes(text: str, cwd: str, targets: dict[str, Target], at: float) -> list[Write]:
    """Writes from each apply_patch envelope embedded in a tool call's input."""
    writes: list[Write] = []
    for match in PATCH_RE.finditer(text):
        body = match.group(1)
        # An envelope inside a quoted string keeps its newlines escaped.
        if "\n" not in body:
            body = unescape(body)
        sections: list[tuple[str, list[str]]] = []
        for line in body.splitlines():
            header = PATCH_FILE_RE.match(line)
            if header:
                sections.append((header.group(1).strip(), []))
            elif line.startswith(PATCH_MOVE) and sections:
                sections[-1] = (line[len(PATCH_MOVE) :].strip(), sections[-1][1])
            elif sections:
                sections[-1][1].append(line)
        for path, lines in sections:
            target = find_target(targets, os.path.join(cwd, path))
            if target is not None:
                writes.append(Write(target.path, at, *patch_lines(lines)))
    return writes


def call_failed(output: object) -> bool:
    if isinstance(output, list):
        output = " ".join(str(item.get("text", "")) for item in output if isinstance(item, dict))
    text = str(output)
    return "Script failed" in text or FAILED_EXIT_RE.search(text) is not None or PATCH_FAILURE_RE.search(text) is not None


def shell_write(command: str, target: Target, at: float) -> Write | None:
    name = re.escape(os.path.basename(target.path))
    redirect = re.search(rf">>?\s*['\"]?[^\s'\"|;&]*{name}", command)
    tee = re.search(rf"\btee\b[^|;&\n]*{name}", command)
    if not (redirect or tee or any(pattern.search(command) for pattern in SHELL_EDIT_RES)):
        return None
    return Write(target.path, at, shell_text=WHITESPACE_RE.sub(" ", command))


def shell_writes(command: str, cwd: str | None, targets: dict[str, Target], at: float) -> list[Write]:
    """Writes by a command that names a target by absolute path, or by file name
    while running inside the target's checkout."""
    writes = []
    for target in targets.values():
        named = target.path in command
        if not named and cwd and os.path.basename(target.path) in command:
            real = realpath(cwd)
            named = real == target.repo or inside_checkout(target.repo, real)
        write = shell_write(command, target, at) if named else None
        if write is not None:
            writes.append(write)
    return writes


def first_text(content: object) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") in ("text", "input_text"):
                return item.get("text")
    return None


def transcripts(root: Path, since: float) -> list[Path]:
    if not root.is_dir():
        return []
    return [path for path in root.rglob("*.jsonl") if path.stat().st_mtime >= since]


def complete_lines(data: bytes) -> list[bytes]:
    """Split a transcript into records, dropping a final record still being written."""
    lines = data.splitlines()
    return lines if data.endswith(b"\n") else lines[:-1]


def claude_metadata(path: Path, session: Session) -> None:
    for raw in complete_lines(path.read_bytes()):
        if session.cwd is None and b'"cwd":"' in raw:
            session.cwd = json.loads(raw).get("cwd")
        if b'"type":"custom-title"' in raw:
            session.title = json.loads(raw).get("customTitle") or session.title
        elif b'"type":"ai-title"' in raw and session.title is None:
            session.title = json.loads(raw).get("aiTitle")
        elif session.first_prompt is None and b'"type":"user"' in raw:
            record = json.loads(raw)
            if record.get("type") == "user" and not record.get("isMeta"):
                text = first_text(record.get("message", {}).get("content"))
                if text and not text.startswith("<local-command"):
                    session.first_prompt = text


def scan_claude(root: Path, since: float, targets: dict[str, Target], sessions: dict[str, Session]) -> None:
    needles = {os.path.basename(path).encode("utf-8") for path in targets}
    for path in transcripts(root / "projects", since):
        data = path.read_bytes()
        if not any(needle in data for needle in needles):
            continue
        errored: set[str] = set()
        pending: list[tuple[str, Write]] = []
        writes: list[Write] = []
        session_id: str | None = None
        for raw in complete_lines(data):
            if b'"is_error":true' in raw:
                for item in json.loads(raw).get("message", {}).get("content", []):
                    if isinstance(item, dict) and item.get("is_error"):
                        errored.add(item.get("tool_use_id"))
            if not any(needle in raw for needle in needles):
                continue
            record = json.loads(raw)
            session_id = session_id or record.get("sessionId")
            result = record.get("toolUseResult")
            if record.get("type") == "user" and isinstance(result, dict) and "filePath" in result:
                target = find_target(targets, result["filePath"])
                if target is None:
                    continue
                if result.get("type") == "create":
                    added, removed = normalized_counts(result["content"].splitlines()), Counter()
                else:
                    added, removed = patch_lines(
                        [line for hunk in result.get("structuredPatch", []) for line in hunk["lines"]]
                    )
                writes.append(Write(target.path, parse_time(record["timestamp"]), added, removed))
            elif record.get("type") == "assistant":
                at = parse_time(record["timestamp"])
                for item in record.get("message", {}).get("content", []):
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        command = item.get("input", {}).get("command")
                        if isinstance(command, str):
                            command_writes = shell_writes(command, record.get("cwd"), targets, at)
                            pending.extend((item.get("id"), write) for write in command_writes)
        writes.extend(write for tool_id, write in pending if tool_id not in errored)
        if not writes or session_id is None:
            continue
        subagent = path.parent.name == "subagents"
        session = sessions.setdefault(f"claude:{session_id}", Session("claude", session_id))
        session.writes.extend(writes)
        session.via_subagent = session.via_subagent or subagent
        main = path.parent.parent.parent / f"{path.parent.parent.name}.jsonl" if subagent else path
        if session.cwd is None and main.is_file():
            claude_metadata(main, session)


def codex_titles(home: Path) -> dict[str, str]:
    index = home / "session_index.jsonl"
    titles: dict[str, str] = {}
    if index.is_file():
        for raw in index.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                record = json.loads(raw)
                titles[record["id"]] = record.get("thread_name")
    return titles


def codex_file_change(item: dict, targets: dict[str, Target], at: float) -> list[Write]:
    writes: list[Write] = []
    if item.get("status") != "completed":
        return writes
    for path, change in item.get("changes", {}).items():
        target = find_target(targets, change.get("move_path") or path)
        if target is None:
            continue
        kind = change.get("type")
        if kind == "update":
            added, removed = patch_lines(change.get("unified_diff", "").splitlines())
        elif kind == "add":
            added, removed = normalized_counts(change.get("content", "").splitlines()), Counter()
        else:
            added, removed = Counter(), normalized_counts(change.get("content", "").splitlines())
        writes.append(Write(target.path, at, added, removed))
    return writes


def scan_codex(home: Path, since: float, targets: dict[str, Target], sessions: dict[str, Session]) -> None:
    needles = {os.path.basename(path).encode("utf-8") for path in targets}
    titles: dict[str, str] | None = None
    for directory, archived in ((home / "sessions", False), (home / "archived_sessions", True)):
        for path in transcripts(directory, since):
            data = path.read_bytes()
            if not any(needle in data for needle in needles):
                continue
            lines = complete_lines(data)
            meta = json.loads(lines[0]).get("payload", {})
            source = meta.get("source")
            subagent = source.get("subagent") if isinstance(source, dict) else None
            if isinstance(subagent, dict) and subagent.get("other") == "guardian":
                continue
            spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
            session_id = spawn["parent_thread_id"] if isinstance(spawn, dict) else meta["id"]
            cwd = meta.get("cwd") or ""

            writes: list[Write] = []
            pending: dict[str, list[Write]] = {}
            first_prompt: str | None = None
            for raw in lines[1:]:
                if first_prompt is None and (b'"UserMessage"' in raw or b'"user_message"' in raw):
                    payload = json.loads(raw).get("payload", {})
                    if payload.get("type") == "user_message":
                        first_prompt = payload.get("message")
                    elif (payload.get("item") or {}).get("type") == "UserMessage":
                        first_prompt = first_text(payload["item"].get("content"))
                call_id = CALL_ID_RE.search(raw) if pending and b"_output" in raw else None
                if call_id and call_id.group(1).decode() in pending:
                    payload = json.loads(raw).get("payload", {})
                    if payload.get("type", "").endswith("_output"):
                        call_writes = pending.pop(payload["call_id"])
                        if not call_failed(payload.get("output")):
                            writes.extend(call_writes)
                if not any(needle in raw for needle in needles):
                    continue
                record = json.loads(raw)
                payload = record.get("payload", {})
                at = parse_time(record["timestamp"])
                if payload.get("type") in ("custom_tool_call", "function_call"):
                    text = str(payload.get("input") or payload.get("arguments") or "")
                    call_writes = envelope_writes(text, cwd, targets, at)
                    if call_writes:
                        pending[payload["call_id"]] = call_writes
                    continue
                item = payload.get("item")
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "FileChange":
                    writes.extend(codex_file_change(item, targets, at))
                elif item.get("type") == "CommandExecution" and item.get("exit_code") == 0:
                    command = item.get("command")
                    command = " ".join(command) if isinstance(command, list) else str(command)
                    command_cwd = str(item.get("cwd") or cwd)
                    if command_cwd.startswith("file://"):
                        command_cwd = unquote(urlparse(command_cwd).path)
                    writes.extend(shell_writes(command, command_cwd, targets, at))
            if not writes:
                continue
            if titles is None:
                titles = codex_titles(home)
            session = sessions.setdefault(f"codex:{session_id}", Session("codex", session_id))
            session.writes.extend(writes)
            session.via_subagent = session.via_subagent or spawn is not None
            session.archived = session.archived or archived
            session.cwd = session.cwd or meta.get("cwd")
            session.title = session.title or titles.get(session_id)
            if spawn is None:
                session.first_prompt = first_prompt


def line_count(target: Target) -> int:
    return sum(target.added.values()) + sum(target.removed.values())


def rank(sessions: dict[str, Session], targets: dict[str, Target]) -> list[Candidate]:
    """Sessions that wrote at least one current changed line, best first."""
    total = sum(line_count(target) for target in targets.values())
    candidates: list[Candidate] = []
    for session in sessions.values():
        matched = 0
        shell_only = 0
        for target in targets.values():
            writes = [write for write in session.writes if write.path == target.path]
            added = sum((write.added for write in writes), Counter())
            removed = sum((write.removed for write in writes), Counter())
            shell = " ".join(write.shell_text for write in writes if write.shell_text)
            for changed, written in ((target.added, added), (target.removed, removed)):
                for text, count in changed.items():
                    direct = min(count, written[text])
                    via_shell = min(count - direct, shell.count(text)) if len(text) >= MIN_SHELL_LINE else 0
                    matched += direct + via_shell
                    shell_only += via_shell
        if matched == 0:
            continue
        reviewer = bool(session.first_prompt and REVIEW_PROMPT_RE.match(session.first_prompt))
        last = max(session.writes, key=lambda write: write.at)
        candidates.append(Candidate(session, reviewer, matched, total, shell_only, last))
    candidates.sort(key=lambda c: (not c.reviewer, c.matched, c.last_write.at), reverse=True)
    return candidates


def local_time(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def resume_command(session: Session) -> str:
    quote = shlex.quote if os.name != "nt" else (lambda text: f'"{text}"')
    command = (
        f"claude --resume {session.session_id}"
        if session.host == "claude"
        else f"codex resume {session.session_id}"
    )
    return f"cd {quote(session.cwd)} && {command}" if session.cwd else command


def describe(candidate: Candidate) -> str:
    session = candidate.session
    role = "reviewer" if candidate.reviewer else "author"
    notes = [note for flag, note in ((session.via_subagent, "via subagent"), (session.archived, "archived")) if flag]
    label = session.title or TAG_RE.sub(" ", session.first_prompt or "")
    label = WHITESPACE_RE.sub(" ", label).strip()[:100] or "(untitled)"
    header = f"{session.host} {role}{' (' + ', '.join(notes) + ')' if notes else ''}: {label}"
    evidence = f"wrote {candidate.matched}/{candidate.total} changed lines"
    if candidate.shell_only:
        evidence += f" ({candidate.shell_only} only through shell commands)"
    last = f"last write {local_time(candidate.last_write.at)}"
    if os.path.exists(candidate.last_write.path):
        delta = os.stat(candidate.last_write.path).st_mtime - candidate.last_write.at
        last += f", {abs(delta):.1f}s {'before' if delta >= 0 else 'after'} the file's mtime"
    return f"{header}\n   {evidence}; {last}\n   {resume_command(session)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="a changed file, or a snippet of changed text")
    parser.add_argument("--days", type=float, default=14, help="transcript age limit (default 14)")
    parser.add_argument("--limit", type=int, default=5, help="candidates to show (default 5)")
    args = parser.parse_args(argv)

    targets, mode = resolve_targets(args.target)
    since = time.time() - args.days * 86400
    sessions: dict[str, Session] = {}
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    scan_claude(claude_home, since, targets, sessions)
    scan_codex(codex_home, since, targets, sessions)

    scope = "snippet lines" if mode == "snippet" else "changed lines vs HEAD"
    for target in targets.values():
        print(f"{target.path}: {line_count(target)} {scope}")
    candidates = rank(sessions, targets)
    if not candidates:
        print(f"\nNo session in the last {args.days:g} days wrote these lines. Try a larger --days.")
        return 1
    print()
    for number, candidate in enumerate(candidates[: args.limit], start=1):
        print(f"{number}. {describe(candidate)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
