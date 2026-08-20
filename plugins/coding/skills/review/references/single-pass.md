# Single-Pass Code Review

Perform one bounded, read-only review of the scope in the task prompt. Return a
final report to the caller; do not ask the user to adjudicate findings and do not
apply fixes.

## Establish the scope

- Review only the supplied diff range, files, and changed lines.
- Use project rules resolved in the task prompt. If none are supplied, read
  `AGENTS.md`, optional `CLAUDE.md`, and relevant design documents before
  judging the change.
- Treat any diff or file content included in the prompt as stale until you read
  the repository state yourself.
- Use the supplied scrutiny list as a starting point, not as a limit.

## What to look for

Search broadly here. Gather every candidate you notice; verification and the
reporting bar below decide what survives. A candidate you never wrote down is one
the filters never get to consider.

**Defects**

- Logic or implementation errors
- Disagreement between documentation and code. Treat neither as automatically
  authoritative; explain what is correct, which may be neither.
- Divergence from requirements, accepted plans, or the task's substantive
  intent. A proposed commit message is metadata, not a requirement.

**Quality observations**

- Violations of the project's design principles or coding standards
- Code that is correct but surprising
- Dead code — suggest deleting it
- Doc comments that have drifted from the implementation, or that merely restate
  the function name — suggest removing
- Missing coverage for critical paths or edge cases
- Test fixtures that need updating

## Separate content from commit mechanics

Review the content that would land. Report a defect when that content produces
a broken tree, omits behavior required by a source other than the commit
message, or otherwise fails the reporting bar below.

Do not report commit mechanics as findings. Commit mechanics include the commit
message's wording or Conventional Commit fields and the choice to include,
combine, split, or order otherwise-valid files or hunks. Never assign these
concerns a priority, and never let them change the verdict. If commit mechanics
are the only concerns, return `Verdict: LAND` and `No issues found.`

Treat a proposed commit message as a fallible summary that can help explain the
change. A mismatch between the message and the diff is a content finding only
when the diff also violates an independent requirement. Otherwise, handle it as
a commit note in the report format below.

## Verify every candidate

This is the first filter. Report only issues that are actually wrong. For each
candidate:

1. Read the implementation, not only the diff.
2. Trace the complete call path and search for all relevant callers and uses.
3. Read nearby comments, tests, history, and design documents that may explain
   the behavior.
4. Construct a concrete failing scenario and compare it with the supplied
   ground truth when one is available.
5. Discard the candidate if an existing guard handles it, the behavior is
   intentional, or the failure cannot be demonstrated.

Do not report style preferences, speculative future risks, feature requests,
issues outside changed lines, or diagnostics a compiler, typechecker, or linter
already reports.

Do not suggest a change that contradicts the project's stated policy in
`AGENTS.md`, `CLAUDE.md`, or design documents read during scoping. Such a
suggestion is a bug in the review, not in the code.

Do not report an issue the code explicitly silences (`// eslint-disable`,
`# noqa`, `@ts-expect-error`, and similar). The author already made that call
deliberately. Report it only if you can prove the suppression itself is wrong.

## Return the report

This is the second filter, and the only place severity decides anything. Of the
candidates that survived verification, report every defect; report a quality
observation only when it is High or Medium impact — one that would change what
the author ships. Drop unlikely corner cases.

Begin with exactly one top-level verdict:

`Verdict: LAND | REVISE | DISCARD`

- **LAND** — the content is worth landing. Commit notes may still recommend
  different packaging.
- **REVISE** — the change is worth landing after the reported defects are fixed.
- **DISCARD** — do not land the change at all because its premise is wrong, it is
  unnecessary, or the problem is already handled elsewhere. This is an expected
  review outcome, not a failure of the review.

Sort findings by severity. For each finding include:

- **Priority:** Critical, High, or Medium
- **Problem:** what fails and the concrete triggering scenario
- **Proof:** the traced path, test, or ground-truth comparison
- **Solution:** a focused correction
- **Location:** `file:line`

Require proof for every finding. If nothing survives verification, return
`No issues found.` after the verdict. Do not pad the report.

After all findings, add a brief `Commit notes` section only when the commit
message or grouping warrants a change. Each note must state the recommendation
and the specific reason it would improve the history. For a message change,
give the complete proposed message. For a split, identify each independently
committable batch and give its complete proposed message. Do not put commit
notes in the findings list or assign them a priority or severity.
