---
name: review
description: Top-level, user-facing code-review workflow for verified issues in specific files, functions, diffs, or code sections. Use when the user directly requests a review and may need to adjudicate its findings. Do not use as an orchestrator for a delegated leaf review or finding-validation task.
---

# Code Review

> Documented in depth: [Most AI code reviews are noise. Here's how to fix that.](https://photostructure.com/coding/claude-code-review/)

Review the mentioned code for potential issues and improvements.

## Leaf-mode guard

If the task identifies your role as `leaf-reviewer` or sets
`delegation-budget: 0`, read and follow
[`references/single-pass.md`](./references/single-pass.md), complete one review
yourself, return the report to the caller, and stop.

## Run the review

Read both references and follow them:

- [`references/single-pass.md`](./references/single-pass.md) — the review method:
  scope, what to look for, verification discipline, exclusions, and the fields
  every finding must carry.
- [`references/orchestration.md`](./references/orchestration.md) — the top-level
  rules: what to study first, the two-leaf delegation bound, and how to present
  findings for the user to adjudicate.

## Adapting for your project

- Replace "the project's coding standards and design principles" in
  `references/orchestration.md` with explicit paths (`AGENTS.md`, optional
  `CLAUDE.md`, `docs/DESIGN-PRINCIPLES.md`).
- Add project-specific "what to look for" items to `references/single-pass.md`
  (e.g. "new public APIs have rate limiting", "DB queries use parameterized
  inputs", "error messages don't leak internal paths").
- Tune the exclusion list in `references/single-pass.md` if your team *does* want
  style or refactor feedback. The default is strict because noise is the bigger
  problem.
