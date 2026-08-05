---
name: review-staged
description: Top-level, user-facing workflow to review the staged Git diff for verified bugs and then prepare a clean Conventional Commit. Use when the user directly asks to review staged changes or prepare their commit. Do not use for a delegated leaf review or finding-validation task.
---

# Review Git Staged Changes

> Documented in depth: [Most AI code reviews are noise. Here's how to fix that.](https://photostructure.com/coding/claude-code-review/)

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

Inspect the scope before reviewing. Past roughly five files or 300 changed lines,
review quality drops sharply; recommend splitting the change before reviewing,
not after. Also decide whether the staged diff tells one coherent story and
recommend a pre-review split when it does not.

Read both references and follow them, with the staged diff as the scope:

- [`../review/references/single-pass.md`](../review/references/single-pass.md) —
  the review method: scope, what to look for, verification discipline,
  exclusions, and the fields every finding must carry, plus the required LAND,
  REVISE, or DISCARD verdict.
- [`../review/references/orchestration.md`](../review/references/orchestration.md) —
  the top-level rules: what to study first, the two-leaf delegation bound, and
  how to present findings for the user to adjudicate.

If the user supplied a proposed commit message, pass it through as the claimed
intent. A diff-versus-message mismatch is a High finding, including scope creep,
a missing half of the claim, or a misdescribed motivation.

## Post-review commit flow

Do NOT commit directly after the review. Follow these steps in order:

If the verdict is DISCARD, explain why the change should not land and stop. Do
not prepare a commit message for a change the review recommends abandoning.

1. List the files (and line ranges, if partial) that are staged for commit.
2. Prepare a
   [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
   message and ask the user to review or edit it before committing. Confirm or
   refine a supplied message; compose one from scratch only when none was
   supplied.
   - **Focus on the _why_, not the _what_** — the diff already shows what changed. One sentence on motivation or consequence beats a list of renamed files.
3. Only commit after explicit user approval.
