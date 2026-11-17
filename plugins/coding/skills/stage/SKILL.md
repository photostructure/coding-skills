---
name: stage
description: Use when committing work from the current session to stage ONLY hunks the session touched, not the entire file. Prevents accidentally staging unrelated uncommitted changes from other work.
metadata:
  website: "https://photostructure.com/coding/clean-commits/#stage"
---

# Stage Session Changes

Stage only changes attributable to the current body of work and compose a
Conventional Commit message.

## User direction

Read and follow the shared [commit instructions](../../references/howto-commit.md).

If all changes from this work are already committed, report that and stop.
Never stage an entire modified file unless every hunk belongs to this work.
Do not use `git add .`, `git add -A`, or `git add --all`.
The bundled [partial-staging helper](scripts/stage_hunks.py) supports
non-interactive staging on Windows and POSIX hosts.

## One concern per commit

When preparing a commit proposal, propose **separate commits** for distinct
concerns unless the user has already specified or approved their grouping.

Signs the session's work should be split:

- Changes span unrelated features, bugs, or subsystems (e.g. a CSS tweak + an unrelated backend fix)
- You'd need "and" in the commit subject to describe it (`fix X and refactor Y`)
- The commit message would exceed 10 lines to explain everything
- Some changes are refactors/cleanup while others are behavior changes
- Tests for feature A are mixed with implementation of feature B

Run the procedure once per proposed commit: inventory that concern, stage it,
compose its message, and commit if authorized. Approval covering several
commits applies to all of them; do not ask again per commit. Honor grouping the
user has already specified or approved.

## Gather live context

Run these commands at invocation time; never rely on embedded or previously
captured output:

```text
git status --short
git diff --cached --stat
git log -5 --format='%h %B'
```

## Procedure

### 1. Inventory Changes to Stage

Review the conversation and operation history. Collect:

- each changed file and the exact before/after content attributable to this
  body of work;
- new files created for this work;
- files deleted for this work.

Files you only inspected are not session changes. Do not stage them.

For work tracked in a plan, read it and attribute any related uncommitted changes
from earlier sessions too. Ask the user when attribution is uncertain. Include
the plan if this session updated it.

### 2. Classify Each File

For each file you changed, run `git diff -- <file>` and compare every hunk with
the recorded changes from this body of work.

| Situation                                 | Action                 |
| ----------------------------------------- | ---------------------- |
| **New file** (`??` in status)             | `git add <file>` only if the whole file belongs to this work |
| **Deleted file**                          | `git rm <file>`        |
| **ALL hunks are yours**                   | `git add <file>`       |
| **SOME hunks are yours** (mixed)          | Partial-stage (step 3) |
| **NO hunks are yours**                    | Do not stage           |

### 3. Partial-stage mixed files

Resolve the bundled helper relative to this skill directory and use the host's
Python 3 launcher. It reads one tracked file's unstaged diff, numbers its hunks,
and passes only explicitly selected hunks to `git apply --cached`; it does not
create a fixed-path temporary file or modify the working tree.

First list the hunks:

```text
python3 scripts/stage_hunks.py path/to/file --list
```

Map each numbered hunk back to the recorded changes for this work. Then stage
only the matching hunk numbers:

```text
python3 scripts/stage_hunks.py path/to/file --include 1,3
```

On Windows, `py -3` is a common equivalent; otherwise use the host's documented
Python 3 launcher. Review the helper's displayed hunk summaries before
applying.

The helper refuses broadened path selections and file-level mode, rename,
copy, creation, or deletion metadata. Attribute and stage those changes
separately before selecting content hunks.

The helper generates its own canonical diff and ignores the repository's diff
configuration (color, prefixes, relative paths, textconv, context, and
inter-hunk context). Always number hunks from `--list` rather than from a plain
`git diff`: a repository that sets `diff.interHunkContext` will merge adjacent
hunks in `git diff` output, so the two numberings can disagree.

If one Git hunk mixes related and unrelated lines, **do not stage that hunk or
the whole file**. Stop and ask the user how to split or attribute the entangled
change. Preserving unrelated work is more important than forcing a commit.

### 4. Verify

```bash
git diff --cached --stat
git diff --cached
```

Every newly staged line must trace to this body of work. Also compare against
the staged diff that existed before this workflow so pre-existing staged work is
not mistaken for yours. If anything is uncertain, stop before committing and
ask the user; never clear or replace someone else's staged changes wholesale.

### 5. Compose Commit Message

Read and follow [commit-message guidance](references/commit-messages.md).
Draft the message from the staged diff, explaining the problem and why the
change solves it. Honor a supplied message and approved grouping.

### 6. Commit When Authorized

If the user has already instructed you to commit or approved the proposed
commit, proceed without another approval request. If the user only asked to
stage changes or prepare a proposal, show the staged diff summary and proposed
message, then wait for commit authorization.

Pass the message to `git commit` using the host's normal non-interactive argument
or message-file mechanism; do not use shell substitution.

After verifying the staged diff contains exactly the intended commit, use plain
`git commit`. Do not use `git commit --only -- <paths>` after partial staging:
`--only` commits the named paths' working-tree content instead of their staged
content, so filtered-out hunks return under a message that does not describe
them.

Use `--only` only for an intended whole-file working-tree commit when you have
not partially staged anything.

Confirm what you are about to commit, not what you staged some minutes ago:

```bash
git diff --cached --stat        # scope
git log -1 --format='%h %s'     # still your commit at the tip?
```

The second matters before any `--amend`: if another session committed while you
were composing, `--amend` rewrites *their* commit. Then the fix is a follow-up
commit or a revert, never an amend.

## Scratch files

Before making repository, build-output, or replay copies, read and follow the
shared [scratch-copy rules](../../references/scratch-files.md).
