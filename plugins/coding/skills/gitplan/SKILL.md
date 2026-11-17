---
name: gitplan
description: Plan and execute coherent Conventional Commit groupings for tangled working tree changes — multiple intertwined logical edits that need to be split into separate, reviewable commits.
metadata:
  website: "https://photostructure.com/coding/clean-commits/#gitplan"
---

# Review and plan git commits

Use this workflow when a working tree mixes logical changes that need separate
commits. File count does not decide applicability. Skip formatter runs, lint
autofixes, typo fixes, and changes that already form one coherent commit.

## User direction

Read and follow the shared [commit instructions](../../references/howto-commit.md).

Honor grouping the user has specified or approved. Otherwise, propose focused
commits and order dependencies before consumers in layered repositories.

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

1. Use the selected theme from Phase 1 as the staging inventory, including its
   related docs and plans, regardless of which session authored the changes.
   Follow [stage](../stage/SKILL.md) steps 2–4 to classify, partially stage, and
   verify those hunks. In those steps, "this work" and "yours" mean the selected
   theme. Stop before committing; the review steps below come first unless
   user direction changes that sequence.
2. **Kick off the second-opinion reviewers on the staged diff, in the background if the host supports it** — step 2 of [`../second-opinion/SKILL.md`](../second-opinion/SKILL.md). Start them first so they run while you review. The reviewers have no staged-only scope, so name the staged file list in the prompt: "review these staged files: `<list>`. The other uncommitted changes belong to later commits; read them where they interact with the staged code. Report any defect the staged diff causes, including in callers or dependencies outside it."
3. Review the staged changes yourself using the shared
   [review method](../review/references/single-pass.md). Return findings to this
   workflow; defer the commit proposal and execution until step 6, after the
   second opinions have been collected and adjudicated.
4. Collect the second opinions, then vet every finding from every review against ground truth and report the result — steps 3-6 of the gate. Accept and veto only with evidence.
5. If fixes are accepted within the review's scope and cost check:
   - Present them clearly with the problem, the proposed fix, and, for a
     defect, its production trigger.
   - Apply fixes incrementally, re-staging as needed.
   - Re-review subject to second-opinion's stop conditions.

   If an Open question needs user direction, report it and wait on that work;
   do not restart the stopped investigation or expand the fix to obtain `LAND`.
6. Present the gate's report, including its pass count and model verdicts, with the proposed commit message, and ask for approval if commit authorization is still missing. When the user approves, commit immediately — no new review or second confirmation.
   - **Commit messages drive the changelog.** The body should describe user-facing behavior changes (what users will see/experience), not just implementation details. Lead with the "what changed for users" — implementation notes are secondary.

For a purely mechanical theme (formatter run, lockfile bump), skip the second
opinion unless project instructions require review before every commit or the
user requests it. Apply **User direction** to commit timing and review overrides.
Report skipped review accurately without adding another permission request.

### Phase 3: Repeat

1. Check `git status` for remaining changes.
2. If more changes exist, return to Phase 1 and pick the next theme.
3. Continue until all changes are committed or the user stops.

## Review Guidelines

The per-theme review in Phase 2 uses the same method and finding format as
`review-staged`, defined in
[`../review/references/single-pass.md`](../review/references/single-pass.md);
don't restate them here.

This skill owns only the grouping decision: whether each theme is a single
coherent commit, and how to split it if not.
