# Single-Pass Code Review

Perform one bounded, read-only review of the scope in the task prompt. Return a
final report to the caller; do not ask the user to adjudicate findings and do not
apply fixes.

## Establish the scope

- Review only the supplied diff range, files, and changed lines.
- Read `AGENTS.md`, optional `CLAUDE.md`, and relevant design documents before
  judging the change.
- Treat any diff or file content included in the prompt as stale until you read
  the repository state yourself.
- Use the supplied scrutiny list as a starting point, not as a limit.

## What to look for

**Defects — always report**

- Logic or implementation errors
- Disagreement between documentation and code. Treat neither as automatically
  authoritative; explain what is correct, which may be neither.
- Divergence from the claimed intent. When the prompt supplies a proposed commit
  message, the diff must deliver exactly what it claims, no more and no less.
  Scope creep, missing halves, and misdescribed motivation are High findings
  even when the code itself is correct.

**Quality observations — report only at High or Medium impact**

- Violations of the project's design principles or coding standards
- Code that is correct but surprising
- Dead code — suggest deleting it
- Doc comments that have drifted from the implementation, or that merely restate
  the function name — suggest removing
- Missing coverage for critical paths or edge cases
- Test fixtures that need updating

An observation that would not change what the author ships is noise; leave it
out. Do not report Low-severity findings or unlikely corner cases at all. A
padded report buries the finding that matters.

## Verify every candidate

Report only issues that are actually wrong. For each candidate:

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

Begin with exactly one top-level verdict:

`Verdict: LAND | REVISE | DISCARD`

- **LAND** — the change is worth landing as written.
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
