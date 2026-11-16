# Code Review Method

Review the scope you were given and report only what you proved.

Do the review yourself. Read the diff, then read the code around it. You may
send a subagent to research background you lack — an unfamiliar library's
semantics, a wire protocol, the behavior of a vendored tool — but the reading,
the verification, and the report are yours.

## Establish the scope

- Review only the supplied diff range, files, and changed lines. Code outside
  them matters only where the change leaves it inconsistent; see **Omissions**
  below.
- Read the repository yourself. Treat any diff or file content pasted into the
  prompt, and any git state gathered earlier in this conversation, as stale.
  This matters most on a follow-up pass, after someone has acted on your last
  report.
- Size the scope first: `git diff --stat` over the review range gives the file
  list and per-file line counts. Discount generated and vendored files — a
  lockfile or snapshot update inflates the count without adding anything to
  review.
- Use project rules resolved in the task prompt. If none are supplied, read
  `AGENTS.md`, optional `CLAUDE.md`, and relevant design documents before
  judging the change.
- If the prompt states what the change is for — a task, a requirement, or a
  commit message — write the expected-change list before you read any hunk of
  the diff: what a complete version of that change must touch, such as callers,
  tests, documentation, configuration, migrations, and error paths. A list
  written after reading the hunks only repeats them.
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
- **Symptom fixes:** a null check, catch, retry, default, clamp, longer timeout,
  or special case added where a bad value arrives instead of where it
  originates, or a test expectation changed to match new output. A symptom fix
  is a defect even when the guard is deliberate. The proof names the origin as
  `file:line` and shows either another path by which the origin still fails or
  the signal the new code hides from callers.
- **Omissions:** dependent code the change left inconsistent with its new
  behavior — a caller, test, document, configuration value, or error path —
  including every item on the expected-change list that the diff does not
  contain and still needs. Report it at the inconsistent line, even when that
  line did not change or is outside the supplied files.

**Unexplained changes**

For each function or branch the change adds or modifies, answer three questions
from what a later reader will have: the code, its tests, its documentation, its
commit history, and the proposed commit message.

1. What requirement or failure does it address?
2. What input reaches it?
3. What breaks if it is deleted?

You need not write the answers down. When you cannot answer one, the change is
**Unexplained**. A change you could explain only from other context pasted into
your prompt is also Unexplained, because the next reader of the code will not
have that prompt.

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

## Screen before building a reproducer

Use the code and existing tests to identify the production trigger and apply
**Rate each defect** before building a reproducer. Drop ruled-out candidates;
put clearly Minor issues in `Minor`. Neither needs a dedicated harness.
Investigate uncertain facts only within the scope check below.

Estimate the work to prove the issue and make the smallest correct fix,
including tests. If either needs a separate implementation effort beyond the
user's task or accepted plan, stop that work. Examples include a new persistence
mechanism, production hooks solely for testing, or a separate simulator. Local
work using existing fixtures can proceed within scope; size alone does not stop
explicitly authorized work.

Record stopped work in `Open questions`: trigger, effect, evidence, whether
proved or suspected, estimated work, and the missing proof or scope decision.
Continue independent work. Open questions keep the verdict `REVISE` until
resolved or explicitly waived; do not build extra machinery to obtain `LAND`.

## Verify every remaining candidate

Report only issues that are actually wrong. For each remaining candidate:

1. Read the implementation, not only the diff.
2. Trace the complete call path and search for all relevant callers and uses.
3. Read nearby comments, tests, history, and design documents that may explain
   the behavior.
4. Construct a concrete failing scenario and compare it with the supplied
   ground truth when one is available.
5. Discard the candidate if an existing guard handles it, the behavior is
   intentional, or the failure cannot be demonstrated.

Steps 4 and 5 do not apply to an Unexplained change. Steps 1–3 are your attempt
to answer its three questions, and the finding stands when that attempt fails.

Do not report style preferences, speculative future risks, feature requests,
problems in unchanged code that the change did not cause, or diagnostics a
compiler, typechecker, or linter already reports.

Do not report arcana, which costs the author a fix and you another pass without
changing what anyone observes:

- Wording in plans, TPPs, handoffs, release notes, documentation, or comments,
  unless a reader who follows the text as written would do the wrong thing: run
  a wrong command, rely on behavior the code does not have, or skip a required
  step. That is a defect; report it with the wrong action as its scenario.
- A defect that the table in **Rate each defect** drops.
- A request to add a guard, check, or fallback against an input that cannot
  reach the code. A guard the change itself adds against such an input is an
  Unexplained change; report it.
- Requests for consistency or terminology changes in code that works.

Do not suggest a change that contradicts the project's stated policy in
`AGENTS.md`, `CLAUDE.md`, or design documents read during scoping. Such a
suggestion is a bug in the review, not in the code.

Do not report an issue the code explicitly silences (`// eslint-disable`,
`# noqa`, `@ts-expect-error`, and similar). The author already made that call
deliberately. Report it only if you can prove the suppression itself is wrong.

## Rate each defect

Describe the production trigger, effect on the user or caller, and recovery.
Support each with code, tests, or field evidence; do not assume severity from
missing facts. A reproduction proves possibility, not real-world frequency.

| Trigger | Disposition |
| --- | --- |
| Normal use, or a failure reported from a real install | Finding for incorrect behavior; Minor for cosmetic issues. |
| A field fault: crash, full disk, lost connection, or concurrent processes/tabs | Finding for unrecoverable data loss or corruption, unauthorized exposure, or a wrong result with no workaround. Otherwise Minor. |
| A contrived sequence with no identified real workflow | Drop. |
| A state or ordering production cannot produce | Drop. |

Normal use includes interaction during pending asynchronous work and crafted
input an untrusted party can send to an exposed interface. Name the callers or
interface that allow it. For field faults, name the interrupted operation.
A real-install report overrides the other trigger categories; cite it.

Judge the whole sequence, not each event in isolation. Explain why ordinary
callers would not produce a sequence you drop as contrived. A narrow timing
window alone does not make it contrived. Mocks and injected delays do not make
a production-reachable failure tests-only; dropping it as impossible requires
naming the production constraint it violates.

For data loss or corruption, identify what the app cannot recover; for exposure,
identify who receives the data. A retry, reload, restart, or automatic recovery
can make a field-fault error Minor. It does not excuse incorrect normal-use
behavior. Cosmetic means behavior remains correct, including any action the
wording tells a reader to take.

A proved defect the user explicitly asked to fix is a finding regardless of
this table. Fix cost affects the scope check, not the disposition.

## Return the report

Report verified defects that **Rate each defect** keeps, and every Unexplained
change. Also report as findings a violation of a rule the project states, dead
code, and a test gap that would let a realistic regression pass.

Put every other survivor — a defect the table rates Minor, a misleading name, a
weak error message or log line, a small test gap around working code, a small
inefficiency — in `Minor` after the findings, one line each with its
`file:line`. Minor items get no ID and no priority, are not tracked across
passes, and never change the verdict. The author may fix them or ignore them
without answering you. Omit the section when it would be empty.

Begin with exactly one top-level verdict:

`Verdict: LAND | REVISE | DISCARD`

- **LAND** — the content is worth landing as it stands. Minor items and commit
  notes may still ride along.
- **REVISE** — the change is worth landing once the reported defects are fixed.
  Any defect you would want fixed before landing makes the verdict `REVISE`; do
  not return `LAND` with defects attached. An Unexplained change also makes the
  verdict `REVISE`: you cannot vouch for code you cannot explain.
- **DISCARD** — do not land the change at all because its premise is wrong, it is
  unnecessary, or the problem is already handled elsewhere. This is an expected
  review outcome, not a failure of the review.

List defects involving unrecoverable data loss, corruption, or unauthorized
exposure first, then other defects, then other findings. For each include:

- **Trigger:** for a defect, the concrete production steps or fault
- **Problem:** what fails and whether recovery is available
- **Proof:** the traced path, test, or ground-truth comparison
- **Solution:** a focused correction
- **Location:** `file:line`

For an Unexplained change, **Problem** names the question you could not answer,
**Proof** lists what you read and why it did not answer the question, and
**Solution** is the question the author must answer.

Require proof for every finding, including one whose fix exceeds scope. Put
stopped work in a separate `Open questions` section: reuse the finding's ID
when the defect is proved, and assign an ID from the same namespace otherwise.
A suspected defect whose investigation the scope and cost check stopped
belongs only in Open questions; discard other undemonstrated candidates under
step 5 of **Verify every remaining candidate**. If neither findings nor
Open questions remain, write `No issues found.` after the verdict; a `Minor`
section may still follow. Do not pad the report.

After all findings, add a brief `Commit notes` section only when the commit
message or grouping warrants a change. Each note must state the recommendation
and the specific reason it would improve the history. For a message change,
give the complete proposed message. For a split, identify each independently
committable batch and give its complete proposed message. Do not put commit
notes in the findings list or assign them a priority or severity.

## Finding IDs

Each review session uses one namespace as its stable handle, so whoever reads
the report can direct feedback to the session that raised a finding. Reuse the
namespace this session already chose. If it has none, run once:

```bash
printf '%03d\n' "$((RANDOM % 1000))"
```

Use the command's sole stdout line unchanged for every review and follow-up in
that session. `$RANDOM` is Bash's pseudorandom integer; do not invent the number
yourself.

Give finding IDs in the form `R<namespace>-A`, then `-B`, `-C`, and so on (for
example, `R123-A` or `R007-B`). IDs must match `^R[0-9]{3}-[A-Z]+$`. Never
prefix a session or finding ID with `#`; models and interfaces may interpret it
as an issue reference. Never use bare IDs such as `A`. IDs do not replace the
written findings.

## Follow-up passes

When you are asked to re-review after someone acted on your report, re-read the
current scope from the repository — every changed file, not only the fixes.
Verify each claimed fix, and weigh the evidence offered for each veto.

Report every prior finding as resolved, still present, or disputed, with a brief
reason, and keep resolved findings separate from current findings. Retain each
existing finding's ID and give new issues the next unused suffix; never recycle
an ID for a different issue. Dispute a veto when its evidence is insufficient,
and say what evidence would settle it. List a Minor item only on the first pass
that notices it.

Carry Open questions forward without repeating the stopped investigation.
Resume that work only when new evidence resolves the question or the user
authorizes the extra scope. A user waiver settles the review disposition;
record it without claiming the defect was fixed or disproved.

An Unexplained change is resolved when its answer is in the code, tests,
documentation, or commit message, including an answer the author shows was
already there. An answer that exists only in the author's reply to you leaves
it still present.

## Stay read-only

A review request is read-only. Do not implement fixes merely because you found
an issue; apply a fix and run its validation only after the requester explicitly
authorizes that change.

After the report, ask whether to accept, veto, or comment on each finding —
unless the prompt says to return the report to a calling agent, in which case
return it and stop. That caller owns adjudication and fixes; do not ask the user
for decisions on its behalf.
