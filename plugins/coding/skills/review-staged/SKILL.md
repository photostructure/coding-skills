---
name: review-staged
description: Top-level, user-facing workflow to review the staged Git diff for verified bugs and then prepare a clean Conventional Commit. Use when the user directly asks to review staged changes or prepare their commit. Do not use for a delegated leaf review or finding-validation task.
metadata:
  website: "https://photostructure.com/coding/claude-code-review/#review-staged"
---

# Review Git Staged Changes

Review the **staged** diff (`git diff --cached`) for potential issues and
improvements, then prepare the commit. When the user supplies a proposed commit
message, use it as context for the intended change, not as a correctness
requirement.

## Leaf-mode guard

If the task identifies your role as `leaf-reviewer` or sets
`delegation-budget: 0`, read and follow
[`../review/references/single-pass.md`](../review/references/single-pass.md),
complete one review yourself, return the report to the caller, and stop before
the commit flow below.

## Run the review

Size the scope before reading it: `git diff --cached --stat`. Review all staged
content as supplied. The size or coherence of a proposed commit does not affect
the review verdict.

With the staged diff as the scope, read and follow
[`../review/references/single-pass.md`](../review/references/single-pass.md), then
[`../review/references/orchestration.md`](../review/references/orchestration.md).
The latter's user-facing response rules replace the former's leaf return
behavior.

After the findings, use the shared `Commit notes` section for optional message
or grouping advice. If a split would improve reviewability or make later reverts
safer, identify the files or hunks in each independently committable batch and
give a complete Conventional Commit message for every batch. State the specific
reason for the split; size alone is not enough. These notes never receive a
priority and never change the verdict. If they are the only concerns, return
`Verdict: LAND` and `No issues found.`

## Post-review commit flow

If the verdict is DISCARD, explain why the change should not land and stop. Do
not prepare a commit message for a change the review recommends abandoning.

Otherwise, do not commit during the review:

1. List the files (and line ranges, if partial) that are staged for commit.
2. Present the recommended commit message, or the batches and messages from the
   `Commit notes` section. When no note was warranted, confirm the supplied
   message or draft one. Emphasize motivation or consequence rather than
   restating the diff. Ask the user to review or edit the proposal.
3. Only commit after explicit user approval.

## Scratch files

Any copy this workflow makes — of the repo, of a build-output directory, of a
file you replay edits onto — belongs in the operating system's temporary
directory, in a fresh directory named for the project and the purpose. Never
inside the checkout, and never under a home directory.

Delete it before you finish. A repo or build-output copy runs to gigabytes,
nothing reaps a home directory, and the out-of-disk failure that eventually
follows surfaces somewhere unrelated — a test suite that hangs, a build that
dies mid-link — costing far more to diagnose than the copy ever saved.
