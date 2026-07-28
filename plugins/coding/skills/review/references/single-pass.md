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

**Correctness**

- Logic or implementation errors
- Code that is correct but surprising — suggest a clearer equivalent or a comment
- Don't trust docs or implementation as authoritative. If they disagree, flag it,
  consider what you think is correct (it may be neither), and explain your
  reasoning

**Code quality**

- Violations of the project's design principles or coding standards
- Dead code — suggest deleting it
- Doc comments that have drifted from the implementation, or that merely restate
  the function name — suggest removing

**Testing and documentation**

- Missing coverage for critical paths or edge cases
- Test fixtures that need updating

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

Do not report an issue the code explicitly silences (`// eslint-disable`,
`# noqa`, `@ts-expect-error`, and similar). The author already made that call
deliberately. Report it only if you can prove the suppression itself is wrong.

## Return the report

Sort findings by severity. For each finding include:

- **Priority:** Critical, High, Medium, or Low
- **Problem:** what fails and the concrete triggering scenario
- **Proof:** the traced path, test, or ground-truth comparison
- **Solution:** a focused correction
- **Location:** `file:line`

Require proof for every finding. If nothing survives verification, return
`No issues found.` Do not pad the report.
