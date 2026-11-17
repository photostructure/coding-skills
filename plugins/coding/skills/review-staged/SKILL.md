---
name: review-staged
description: Workflow to review the staged Git diff for verified bugs and then prepare a clean Conventional Commit. Use when the user directly asks to review staged changes or prepare a commit proposal. Do not trigger on a direct commit instruction without a review request.
metadata:
  website: "https://photostructure.com/coding/claude-code-review/#review-staged"
---

# Review Git Staged Changes

Review the **staged** diff (`git diff --cached`) for potential issues and
improvements, then prepare the commit. When the user supplies a proposed commit
message, use it as context for the intended change, not as a correctness
requirement.

## User direction

Read and follow the shared [commit instructions](../../references/howto-commit.md).

## Run the review

Size the scope before reading it: `git diff --cached --stat`. Review all staged
content as supplied. The size or coherence of a proposed commit does not affect
the review verdict.

With the staged diff as the scope, read and follow
[`../review/references/single-pass.md`](../review/references/single-pass.md).

After the findings, use the shared `Commit notes` section for optional message
or grouping advice. If a split would improve reviewability or make later reverts
safer, identify the files or hunks in each independently committable batch and
give a complete Conventional Commit message for every batch. State the specific
reason for the split; size alone is not enough. These notes never receive a
priority and never change the verdict. If they are the only concerns, return
`Verdict: LAND` and `No issues found.`

## Post-review commit flow

If the verdict is DISCARD, explain why the change should not land and stop the
review. A later user instruction to commit takes precedence as described in
**User direction**.

If the report has Open questions, report them and wait for the user, even after
"commit when ready" or "review, then commit". An instruction to "commit now"
still commits.

Otherwise:

1. List the files (and line ranges, if partial) that are staged for commit.
2. Present the recommended commit message, or the batches and messages from the
   `Commit notes` section. When no note was warranted, confirm the supplied
   message or draft one. Emphasize motivation or consequence rather than
   restating the diff.
3. If the user already authorized committing this scope, such as "review, then
   commit", proceed within those instructions without asking again. Otherwise,
   ask the user to approve or edit the proposal and wait for commit authorization.

## Scratch files

Before making repository, build-output, or replay copies, read and follow the
shared [scratch-copy rules](../../references/scratch-files.md).
