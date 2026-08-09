---
name: review-staged
description: Top-level, user-facing workflow to review the staged Git diff for verified bugs and then prepare a clean Conventional Commit. Use when the user directly asks to review staged changes or prepare their commit. Do not use for a delegated leaf review or finding-validation task.
---

# Review Git Staged Changes

Review the **staged** diff (`git diff --cached`) for potential issues and
improvements, then prepare the commit. When the user supplies a proposed commit
message, treat it as the claimed intent and review the diff against it.

## Leaf-mode guard

If the task identifies your role as `leaf-reviewer` or sets
`delegation-budget: 0`, read and follow
[`../review/references/single-pass.md`](../review/references/single-pass.md),
complete one review yourself, return the report to the caller, and stop before
the commit flow below.

## Run the review

Size the scope before reading it: `git diff --cached --stat`. Recommend a split —
before the review, not after — when the staged diff does not tell one coherent
story. Size alone is not a reason to split: staging is already an act of
selection, and a large change that tells one story rarely decomposes into
independently committable pieces after the fact.

With the staged diff as the scope, read and follow
[`../review/references/single-pass.md`](../review/references/single-pass.md), then
[`../review/references/orchestration.md`](../review/references/orchestration.md).
The latter's user-facing response rules replace the former's leaf return
behavior.

## Post-review commit flow

If the verdict is DISCARD, explain why the change should not land and stop. Do
not prepare a commit message for a change the review recommends abandoning.

Otherwise, do not commit during the review:

1. List the files (and line ranges, if partial) that are staged for commit.
2. Confirm or refine the supplied Conventional Commit message, or draft one when
   none was supplied. Emphasize motivation or consequence rather than restating
   the diff. Ask the user to review or edit it.
3. Only commit after explicit user approval.
