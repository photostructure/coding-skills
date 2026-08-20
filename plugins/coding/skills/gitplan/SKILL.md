---
name: gitplan
description: Plan and execute coherent Conventional Commit groupings for tangled working tree changes — multiple intertwined logical edits that need to be split into separate, reviewable commits.
metadata:
  website: "https://photostructure.com/coding/clean-commits/#gitplan"
---

**Applicability is about how tangled the changes are, not how many files they touch.** Invoke this skill when the working tree mixes multiple intertwined logical changes that need untangling into separate commits — even if that's only a handful of files. Skip it when the changes are trivial or superficial, no matter how many files they touch: formatter runs, lint autofixes, typo/grammar fixes, or edits that obviously belong in a single commit.

# Review and plan git commits

> More on these workflows: [photostructure.com/coding](https://photostructure.com/coding/)

**Never create megacommits.** Each commit should be focused, coherent, and reviewable.

If the repository has a layered structure (e.g. shared utilities → core → feature packages → app), work through it from the lowest-level layer upward so dependencies are committed before their consumers.

## Workflow

### Phase 1: Identify Themes

1. Scan all current changes with `git status` and `git diff --stat`. When
   subagents are available and the diff is large, use them to preserve context
   and summarize distinct areas.
2. For complex diffs, use `git diff -U150` but limit JSON/lockfiles to the first ~50 lines.
3. Identify logical themes/groupings. Each theme must have a **single coherent purpose** — a unifying "why" that explains every file in the group. If you can't state the purpose in one sentence without using "and", split the theme. **Never create catch-all buckets** like "housekeeping", "misc", "cleanup", or "various fixes". Every file belongs in a theme because of what it _does_, not because it's small or doesn't fit elsewhere. Orphan files that truly don't relate to any theme get their own single-file commit.
4. **Bundle related docs/plans with their code changes.** If a planning doc, design note, or task file corresponds to a theme, commit it alongside the code it describes — never lump it into a separate "docs" commit. Docs that don't correspond to any code change can go in a docs-only commit.
5. Present the themes to the user as a numbered list with brief descriptions. Order by increasing complexity/risk.
6. Ask: "Which theme should we focus on first?"

### Phase 2: Stage, Review, and Commit (per theme)

1. Stage only files belonging to the selected theme using `git add <files>`, including any related docs/plans decided in Phase 1.
2. **Kick off the cross-model second opinion on the staged diff, in the background if the host supports it** — step 2 of [`../second-opinion/SKILL.md`](../second-opinion/SKILL.md). Start it first so it runs while you review. The external reviewer has no staged-only scope, so name the staged file list in the prompt: "review only these staged files: `<list>`; the other uncommitted changes belong to later commits — ignore them."
3. Review the staged changes yourself using the `review-staged` skill. Use a capable model — reviews are important.
4. Collect the second opinion, then vet every finding from both passes against ground truth — steps 3-5 of the gate. Accept and veto only with evidence.
5. If issues are accepted:
   - Present them clearly with priority, problem, and proposed fix.
   - Apply fixes incrementally, re-staging as needed.
   - Re-review until clean.
6. Present the proposed commit message and ask for approval. When the user approves, commit immediately — no second confirmation.
   - **Commit messages drive the changelog.** The body should describe user-facing behavior changes (what users will see/experience), not just implementation details. Lead with the "what changed for users" — implementation notes are secondary.

Skip the second opinion only when the user asks you to, or when the theme is
purely mechanical (formatter run, lockfile bump). Say so when you skip it.

### Phase 3: Repeat

1. Check `git status` for remaining changes.
2. If more changes exist, return to Phase 1 and pick the next theme.
3. Continue until all changes are committed or the user stops.

## Review Guidelines

The per-theme review in Phase 2 is the `review-staged` workflow. Its method,
delegation bound, and finding format live in
[`../review/references/single-pass.md`](../review/references/single-pass.md) and
[`../review/references/orchestration.md`](../review/references/orchestration.md);
don't restate them here.

This skill owns only the grouping decision: whether each theme is a single
coherent commit, and how to split it if not.
