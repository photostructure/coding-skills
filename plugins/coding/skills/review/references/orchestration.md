# Top-Level Review Orchestration

Shared rules for a user-facing review workflow. Apply the review method in
[`single-pass.md`](./single-pass.md), but use the response and user-interaction
rules here instead of that file's leaf return behavior.

Treat any git state, diff, or file content gathered earlier in this conversation
as stale and re-read it from the repository, especially when the user re-runs
this skill after acting on an earlier review.

## Delegate only when needed

Review locally by default. Size the scope before reading it: `git diff --stat`
over the review range gives the file list and per-file line counts for a few
dozen lines of context. Discount generated and vendored files — a lockfile or
snapshot update inflates the count without adding anything to review.

Delegate only when that measurement clears roughly ten first-party files or a
thousand first-party changed lines *and* the surrounding code needed to judge
them will not fit in your remaining context. Below that bar, read the diff and
review it yourself. Finishing sooner is not a reason to delegate.

Do not delegate merely to repeat the primary pass, obtain a second opinion, or
revalidate candidates. The parent owns final verification. Use no more than two
leaf tasks and one delegation round, partitioned along the file list from the
stat so no two leaves overlap.

Resolve common context once: the exact scope, substantive intent, commit
metadata if supplied, applicable project rules, and scrutiny focus. Pass that
concise context and the relevant source paths to each leaf; do not make leaves
repeat this discovery or pass them the full conversation.

If the current host exposes the tool-restricted `coding:reviewer` agent, use it.
Otherwise use a general task-local subagent. Start every leaf prompt with
`role: leaf-reviewer` and `delegation-budget: 0`, point it at the resolved path
of `<plugin-root>/skills/review/references/single-pass.md`, omit workflow skill
names, and require one final report. When no leaf mechanism is available,
continue locally.

## Response format

Use the verdict, severity order, and finding fields from
[`single-pass.md`](./single-pass.md). Each reviewer agent session uses one
namespace as its stable handle, so the user can direct feedback to the agent
that reported a finding. Reuse the namespace this session chose earlier. If it
has none, run once:

```bash
printf '%03d\n' "$((RANDOM % 1000))"
```

Use the command's sole stdout line unchanged for every review and follow-up in
that session. `$RANDOM` is Bash's pseudorandom integer; do not invent the number
yourself.

Give findings IDs in the form `#<namespace>-A`, then `-B`, `-C`, and so on (for
example, `#123-A` or `#007-B`). IDs must match `^#[0-9]{3}-[A-Z]+$`; never use
bare IDs such as `#A`. After the complete report, ask the user whether to accept,
veto, or comment on each finding; IDs do not replace the written findings.

A review request is read-only. Do not implement fixes merely because you found
an issue; apply a fix and run its validation only after the user explicitly
authorizes that change.
