# Top-Level Review Orchestration

Shared rules for a user-facing review workflow. Apply the review method in
[`single-pass.md`](./single-pass.md), but use the response and user-interaction
rules here instead of that file's leaf return behavior.

## Before you start

Study the project's coding standards and design principles — start with
`AGENTS.md`, then honor `CLAUDE.md` and relevant design docs when present.

Review critically. Question every design choice and flag anything that would
fail a production code review. Assume any git state or file contents gathered
earlier is stale, especially if the user re-runs this skill or asks you to
re-read.

## Bounded delegation

Perform the primary review yourself. Use at most **two** additional leaf-review
tasks for the entire review. Do not launch one task per file or per finding, and
do not launch a second iteration round.

- For a large or complex change, use one leaf to cover a coherent file group or
  a distinct perspective such as repository-guidance compliance or historical
  context.
- If candidates survive your own pass, use one leaf to validate all candidates
  together, explicitly asking it to disprove them by tracing missed guards,
  callers, and design constraints.

If the current host exposes the tool-restricted `coding:reviewer` agent, use it.
Otherwise use a general task-local subagent. Start every leaf prompt with
`role: leaf-reviewer` and `delegation-budget: 0`, point it at the resolved path
of `<plugin-root>/skills/review/references/single-pass.md`, omit workflow skill
names, and require one final report. When context inheritance is configurable,
do not pass the surrounding conversation. When no leaf mechanism is available,
perform the same exploration and validation yourself.

## Response format

Omit any issue that turned out to be noise after research. Sort the rest by
severity (Critical → High → Medium). Do not report Low-severity findings or
unlikely corner cases. Begin with the LAND, REVISE, or DISCARD verdict required
by [`single-pass.md`](./single-pass.md). If nothing survives, say "No issues
found." after the verdict. Do not pad the list.

**Step 1 — write up every issue as text first.** Give each a short ID (`#A`,
`#B`) and the fields listed in [`single-pass.md`](./single-pass.md): Priority,
Problem, Proof, Solution, Location.

**Step 2 — only after all issue blocks are written**, ask the user normally
whether to accept, veto, or comment on each one. Refer to the short IDs, but do
not use an ID-only question as a substitute for the write-up.

A review request is read-only. Do not implement fixes merely because you found
an issue; apply a fix and run its validation only after the user explicitly
authorizes that change.
