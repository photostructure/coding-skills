#!/usr/bin/env python3
"""Tests for find_session.py."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("find_session.py")
STAMP = "2026-01-02T03:04:05.000Z"
BASE = "def main():\n    return 0\n"
CHANGED = (
    "def main():\n"
    "    # Retry the upload when the server drops the connection,\n"
    "    # because the client cannot tell a drop from a refusal.\n"
    "    value = compute_total(items)\n"
    "    return 0\n"
)
COMMENT_HUNK = [
    " def main():",
    "+    # Retry the upload when the server drops the connection,",
    "+    # because the client cannot tell a drop from a refusal.",
]
VALUE_HUNK = ["+    value = compute_total(items)", "     return 0"]
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def dump(records: list[dict]) -> str:
    # Both CLIs write compact JSON, and the finder's byte prefilters rely on it.
    return "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records)


class FindSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="find-session-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / "repo"
        self.claude_home = self.root / "claude"
        self.codex_home = self.root / "codex"
        self.repo.mkdir()
        self.file = self.repo / "app.py"
        self.file.write_text(BASE, encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "app.py")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "base")
        self.file.write_text(CHANGED, encoding="utf-8")

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.repo, env={**os.environ, **GIT_ENV}, check=True)

    def run_finder(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            **GIT_ENV,
            "CLAUDE_CONFIG_DIR": str(self.claude_home),
            "CODEX_HOME": str(self.codex_home),
        }
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    def resume_line(self, host: str, session_id: str) -> str:
        command = f"claude --resume {session_id}" if host == "claude" else f"codex resume {session_id}"
        return f"   cd {shlex.quote(str(self.repo))} && {command}"

    # Claude Code transcripts

    def claude_transcript(self, session_id: str, records: list[dict], *, subagent: bool = False) -> Path:
        project = self.claude_home / "projects" / "-repo"
        path = project / session_id / "subagents" / "agent-a1.jsonl" if subagent else project / f"{session_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(records), encoding="utf-8")
        return path

    def claude_prompt(self, session_id: str, text: str) -> dict:
        return {
            "type": "user",
            "sessionId": session_id,
            "cwd": str(self.repo),
            "timestamp": STAMP,
            "message": {"role": "user", "content": text},
        }

    def claude_edit(self, session_id: str, lines: list[str], path: Path | None = None) -> dict:
        return {
            "type": "user",
            "sessionId": session_id,
            "timestamp": STAMP,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_edit", "content": "ok"}]},
            "toolUseResult": {
                "filePath": str(path or self.file),
                "structuredPatch": [{"oldStart": 1, "oldLines": 2, "newStart": 1, "newLines": 4, "lines": lines}],
            },
        }

    def claude_command(self, session_id: str, tool_id: str, command: str) -> dict:
        return {
            "type": "assistant",
            "sessionId": session_id,
            "cwd": str(self.repo),
            "timestamp": STAMP,
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": tool_id, "name": "Bash", "input": {"command": command}}],
            },
        }

    def claude_rejection(self, session_id: str, tool_id: str) -> dict:
        return {
            "type": "user",
            "sessionId": session_id,
            "timestamp": STAMP,
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": tool_id, "is_error": True, "content": "rejected"}],
            },
        }

    # Codex rollouts

    def codex_rollout(self, session_id: str, records: list[dict], *, source: object = "cli", title: str | None = None) -> Path:
        path = self.codex_home / "sessions" / "2026" / "01" / "02" / f"rollout-2026-01-02T03-04-05-{session_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {"timestamp": STAMP, "type": "session_meta", "payload": {"id": session_id, "cwd": str(self.repo), "source": source}}
        path.write_text(dump([meta, *records]), encoding="utf-8")
        if title is not None:
            with (self.codex_home / "session_index.jsonl").open("a", encoding="utf-8") as index:
                index.write(dump([{"id": session_id, "thread_name": title}]))
        return path

    def codex_item(self, item: dict) -> dict:
        return {"timestamp": STAMP, "type": "event_msg", "payload": {"type": "item_completed", "item": item}}

    def codex_prompt(self, text: str) -> dict:
        return self.codex_item({"type": "UserMessage", "content": [{"type": "text", "text": text}]})

    def codex_file_change(self, diff_lines: list[str], *, path: Path | None = None, status: str = "completed") -> dict:
        change = {"type": "update", "unified_diff": "@@ -1,2 +1,4 @@\n" + "\n".join(diff_lines) + "\n", "move_path": None}
        return self.codex_item({"type": "FileChange", "status": status, "changes": {str(path or self.file): change}})

    def codex_exec(self, call_id: str, code: str, output: str) -> list[dict]:
        return [
            {"timestamp": STAMP, "type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "call_id": call_id, "input": code}},
            {
                "timestamp": STAMP,
                "type": "response_item",
                "payload": {"type": "custom_tool_call_output", "call_id": call_id, "output": [{"type": "input_text", "text": output}]},
            },
        ]

    # Tests

    def test_file_attributes_the_author_and_prints_its_resume_command(self) -> None:
        self.claude_transcript(
            "c-author",
            [
                self.claude_prompt("c-author", "Make uploads retry"),
                {"type": "custom-title", "customTitle": "Upload retries", "sessionId": "c-author"},
                self.claude_edit("c-author", COMMENT_HUNK + VALUE_HUNK),
            ],
        )
        self.codex_rollout(
            "x-reviewer",
            [
                self.codex_prompt("$coding:review\n\nReview the change below."),
                self.codex_item({"type": "CommandExecution", "command": ["git", "diff", "--", "app.py"], "exit_code": 0}),
            ],
            source="exec",
        )

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"{self.file}: 3 changed lines vs HEAD", result.stdout)
        self.assertIn("1. claude author: Upload retries\n   wrote 3/3 changed lines", result.stdout)
        self.assertIn(self.resume_line("claude", "c-author"), result.stdout.splitlines())
        self.assertNotIn("x-reviewer", result.stdout)

    def test_author_ranks_before_a_reviewer_that_wrote_more(self) -> None:
        self.codex_rollout(
            "x-author",
            [self.codex_prompt("Add the retry comment"), self.codex_file_change(COMMENT_HUNK[:2])],
            title="Retry comment",
        )
        review_prompt = (
            "<command-message>coding:review</command-message>\n"
            "<command-name>/coding:review</command-name>\n<command-args>Review this</command-args>"
        )
        self.claude_transcript(
            "c-reviewer",
            [self.claude_prompt("c-reviewer", review_prompt), self.claude_edit("c-reviewer", COMMENT_HUNK + VALUE_HUNK)],
        )

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 0, result.stderr)
        author = result.stdout.index("1. codex author: Retry comment\n   wrote 1/3 changed lines")
        reviewer = result.stdout.index("2. claude reviewer:")
        self.assertLess(author, reviewer)
        self.assertIn(self.resume_line("codex", "x-author"), result.stdout.splitlines())

    def test_prompt_that_mentions_review_later_is_an_author(self) -> None:
        self.claude_transcript(
            "c-mixed",
            [
                self.claude_prompt("c-mixed", "The intern left. We need to /coding:review the diff, then fix it."),
                self.claude_edit("c-mixed", VALUE_HUNK),
            ],
        )

        result = self.run_finder("app.py")

        self.assertIn("1. claude author:", result.stdout)

    def test_snippet_across_comment_lines_finds_only_that_block_writer(self) -> None:
        self.claude_transcript("c-comment", [self.claude_prompt("c-comment", "comment"), self.claude_edit("c-comment", COMMENT_HUNK)])
        self.claude_transcript("c-value", [self.claude_prompt("c-value", "value"), self.claude_edit("c-value", VALUE_HUNK)])

        result = self.run_finder("drops the connection,\n  because the client cannot")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"{self.file}: 2 snippet lines", result.stdout)
        self.assertIn(self.resume_line("claude", "c-comment"), result.stdout.splitlines())
        self.assertNotIn("c-value", result.stdout)

    def test_snippet_missing_from_the_diff_fails(self) -> None:
        result = self.run_finder("text that no change contains")

        self.assertEqual(result.returncode, 1)
        self.assertIn("contains the snippet: 'text that no change contains'", result.stderr)

    def test_code_mode_patch_counts_unless_its_script_failed(self) -> None:
        patch = "*** Begin Patch\n*** Update File: app.py\n@@\n" + "\n".join(VALUE_HUNK) + "\n*** End Patch\n"
        # Code mode passes the envelope as a JavaScript string literal.
        code = f"const patch = {json.dumps(patch)};\nawait tools.write_stdin({{session_id: 1, chars: patch}});"
        self.codex_rollout("x-applied", self.codex_exec("call_ok", code, "Script completed\nOutput:\n"), title="Applied")
        self.codex_rollout("x-failed", self.codex_exec("call_bad", code, "Script failed\nScript error: verification failed"))

        result = self.run_finder("app.py")

        self.assertIn("1. codex author: Applied\n   wrote 1/3 changed lines", result.stdout)
        self.assertNotIn("x-failed", result.stdout)

    def test_failed_file_change_and_rejected_shell_write_are_ignored(self) -> None:
        self.codex_rollout("x-failed", [self.codex_file_change(VALUE_HUNK, status="failed")])
        script = "python3 - <<'PY'\nfrom pathlib import Path\np = Path('app.py')\np.write_text(p.read_text().replace('    return 0', '    value = compute_total(items)\\n    return 0'))\nPY"
        self.claude_transcript(
            "c-rejected",
            [self.claude_command("c-rejected", "toolu_1", script), self.claude_rejection("c-rejected", "toolu_1")],
        )

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 1)
        self.assertIn("No session in the last 14 days wrote these lines", result.stdout)

    def test_shell_write_counts_as_weaker_evidence(self) -> None:
        script = "python3 - <<'PY'\nfrom pathlib import Path\np = Path('app.py')\np.write_text(p.read_text().replace('    return 0', '    value = compute_total(items)\\n    return 0'))\nPY"
        self.claude_transcript("c-shell", [self.claude_prompt("c-shell", "edit"), self.claude_command("c-shell", "toolu_1", script)])

        result = self.run_finder("app.py")

        self.assertIn("wrote 1/3 changed lines (1 only through shell commands)", result.stdout)

    def test_shell_write_in_another_checkout_does_not_count(self) -> None:
        script = "python3 - <<'PY'\nfrom pathlib import Path\np = Path('app.py')\np.write_text(p.read_text().replace('    return 0', '    value = compute_total(items)\\n    return 0'))\nPY"
        command = self.claude_command("c-elsewhere", "toolu_1", script)
        command["cwd"] = str(self.root / "other-checkout")
        self.claude_transcript("c-elsewhere", [self.claude_prompt("c-elsewhere", "edit"), command])

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 1, result.stdout)

    def test_subagent_write_resumes_the_parent_session(self) -> None:
        self.claude_transcript(
            "c-parent",
            [self.claude_prompt("c-parent", "Delegate it"), {"type": "custom-title", "customTitle": "Parent", "sessionId": "c-parent"}],
        )
        self.claude_transcript("c-parent", [self.claude_edit("c-parent", VALUE_HUNK)], subagent=True)

        result = self.run_finder("app.py")

        self.assertIn("1. claude author (via subagent): Parent", result.stdout)
        self.assertIn(self.resume_line("claude", "c-parent"), result.stdout.splitlines())

    def test_write_before_the_file_moved_counts(self) -> None:
        old_path = self.repo / "old" / "app.py"
        self.codex_rollout("x-moved", [self.codex_prompt("write"), self.codex_file_change(VALUE_HUNK, path=old_path)])

        result = self.run_finder("app.py")

        self.assertIn(self.resume_line("codex", "x-moved"), result.stdout.splitlines())

    def test_deleted_path_in_another_checkout_is_not_a_move(self) -> None:
        (self.repo / ".gitignore").write_text("worktrees/\n", encoding="utf-8")
        elsewhere = self.root / "other-checkout" / "app.py"
        ignored = self.repo / "worktrees" / "agent" / "app.py"
        self.codex_rollout("x-elsewhere", [self.codex_prompt("write"), self.codex_file_change(VALUE_HUNK, path=elsewhere)])
        self.codex_rollout("x-ignored", [self.codex_prompt("write"), self.codex_file_change(VALUE_HUNK, path=ignored)])

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 1, result.stdout)

    def test_patch_output_reporting_failure_is_ignored(self) -> None:
        patch = "*** Begin Patch\n*** Update File: app.py\n@@\n" + "\n".join(VALUE_HUNK) + "\n*** End Patch\n"
        outputs = {
            "x-unverified": "apply_patch verification failed: Failed to find expected lines in app.py",
            "x-rejected": "patch rejected: writing outside of the project; rejected by user approval settings",
        }
        for session_id, output in outputs.items():
            call = {"type": "custom_tool_call", "name": "apply_patch", "call_id": f"call_{session_id}", "input": patch}
            reply = {"type": "custom_tool_call_output", "call_id": f"call_{session_id}", "output": output}
            self.codex_rollout(
                session_id,
                [{"timestamp": STAMP, "type": "response_item", "payload": payload} for payload in (call, reply)],
            )

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 1, result.stdout)

    def test_repeated_lines_count_each_occurrence(self) -> None:
        self.file.write_text(
            "def main():\n"
            + "    retry_upload(connection)\n" * 8
            + "    log_attempt(total)\n    report_status(code)\n    return 0\n",
            encoding="utf-8",
        )
        self.claude_transcript(
            "c-repeated",
            [self.claude_prompt("c-repeated", "repeat"), self.claude_edit("c-repeated", ["+    retry_upload(connection)"] * 8)],
        )
        self.claude_transcript(
            "c-distinct",
            [
                self.claude_prompt("c-distinct", "distinct"),
                self.claude_edit("c-distinct", ["+    log_attempt(total)", "+    report_status(code)"]),
            ],
        )

        result = self.run_finder("app.py")

        self.assertIn(f"{self.file}: 10 changed lines vs HEAD", result.stdout)
        self.assertIn("1. claude author: repeat\n   wrote 8/10 changed lines", result.stdout)
        self.assertIn("2. claude author: distinct\n   wrote 2/10 changed lines", result.stdout)

    def test_guardian_subagents_are_skipped(self) -> None:
        guardian = {"subagent": {"other": "guardian"}}
        self.codex_rollout("x-guardian", [self.codex_file_change(VALUE_HUNK)], source=guardian)

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 1)

    def test_record_still_being_written_is_ignored(self) -> None:
        path = self.claude_transcript("c-live", [self.claude_prompt("c-live", "edit"), self.claude_edit("c-live", VALUE_HUNK)])
        with path.open("a", encoding="utf-8") as transcript:
            transcript.write('{"type":"assistant","sessionId":"c-live","message":{"content":"app.py')

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.resume_line("claude", "c-live"), result.stdout.splitlines())

    def test_transcripts_older_than_the_window_are_skipped(self) -> None:
        path = self.claude_transcript("c-old", [self.claude_prompt("c-old", "edit"), self.claude_edit("c-old", VALUE_HUNK)])
        month_ago = time.time() - 30 * 86400
        os.utime(path, (month_ago, month_ago))

        self.assertEqual(self.run_finder("app.py").returncode, 1)
        self.assertIn(self.resume_line("claude", "c-old"), self.run_finder("app.py", "--days", "60").stdout.splitlines())

    def test_untracked_file_counts_every_line_as_added(self) -> None:
        new_file = self.repo / "notes.md"
        new_file.write_text("Uploads retry after a dropped connection.\n", encoding="utf-8")
        create = {
            "type": "user",
            "sessionId": "c-new",
            "timestamp": STAMP,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_w", "content": "ok"}]},
            "toolUseResult": {"type": "create", "filePath": str(new_file), "content": new_file.read_text(encoding="utf-8")},
        }
        self.claude_transcript("c-new", [self.claude_prompt("c-new", "write notes"), create])

        result = self.run_finder("notes.md")

        self.assertIn("wrote 1/1 changed lines", result.stdout)
        self.assertIn(self.resume_line("claude", "c-new"), result.stdout.splitlines())

    def test_unchanged_file_fails(self) -> None:
        self.git("checkout", "--", "app.py")

        result = self.run_finder("app.py")

        self.assertEqual(result.returncode, 1)
        self.assertIn("app.py has no uncommitted changes against HEAD", result.stderr)


if __name__ == "__main__":
    unittest.main()
