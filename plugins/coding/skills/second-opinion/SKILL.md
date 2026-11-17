---
name: second-opinion
description: Get second opinions on freshly written code from fresh Codex and Claude reviewers, then settle every finding against ground truth before accepting or vetoing it. Use when requested, when project instructions require review before commits, or as part of an active review workflow after tests pass.
metadata:
  website: "https://photostructure.com/coding/claude-code-review/#second-opinion"
---

# Second Opinion

Give fresh Codex and Claude sessions the complete requested review scope, then
settle their findings against evidence. Fresh reviewers can challenge the
author's assumptions. Do not split agent reviews to meet a line count or
reading-time budget; those limits belong to human gavel reviews.

1. Prepare the scope, proposed commit message, requirements, and ground truth.
2. Run both reviewers and read the same code yourself.
3. Accept, veto, or leave open each finding, with evidence.
4. Test and fix accepted findings within scope.
5. Re-review in the same sessions, subject to the stop rules in step 5.
6. Report findings, dispositions, and both reviewers' verdicts.

## User direction

Read and follow the shared [commit instructions](../../references/howto-commit.md).

## 1. List what you changed

Write down, for the prompt you are about to send:

- **The changed files and how to diff them** — the exact diff command and an
  explicit repository-relative file list. Distinguish staged hunks from
  unstaged changes in the same file, and name in-scope untracked files
  separately, because an ordinary diff omits them.
- **The proposed commit message** — verbatim when the user supplied one,
  otherwise drafted from the task and the current diff. Label it as a fallible
  summary, not a correctness requirement. When the tree holds several logical
  changes, follow [stage](../stage/SKILL.md) and give the file list and the
  proposed message for each commit.
- **The task and its requirements** — the user's request and any accepted plan
  or specification needed to judge behavior. Give repository paths for project
  rules and design documents; the reviewer can open them. Paste only what it
  cannot reach, such as decisions made only in conversation.
- **The ground truth** — the thing a disputed finding can be tested against: a
  reference implementation you can execute, a spec with runnable examples, the
  real API. Write the *exact command* that queries it. No executable ground
  truth? Say so, and name the fallback (spec text, maintainer ruling).

Leave out your suspected findings, your interim conclusions, and any scrutiny
list the user or the project did not supply. An independent read is the whole
point; steering it costs you the findings you could not have made yourself.
Never mark changed code, its callers, or code it depends on as out of scope or
"context only". Additional context explains decisions; it does not narrow the
review.

## 2. Ask both models

Both reviewers start in fresh processes without this session's context. They
share the working tree, so reproduce reported build or test failures before
accepting them; a concurrent run may have caused the failure.

Read and follow the [reviewer CLI protocol](references/reviewer-cli.md) before
launching either reviewer. It owns the commands, model and effort flags,
authorization checks, prompt template, result validation, and fallbacks.
Run both reviewers concurrently with the step 1 inputs.

**Read the new code yourself while the reviewers run** — you are the third
reviewer, and the only one who knows the full context of what the change was
supposed to do. Hold your edits until both reports arrive. The reviewers read
the repository live, so a file that changes mid-pass gives them a tree that
never existed. Write down what you find and adjudicate it in step 3.

## 3. Adjudicate every finding

Apply the [review method](../review/references/single-pass.md) to both
reviewers' findings and your own. A `LAND` label does not excuse unresolved
findings or Open questions. Reviewer agreement and confidence are not evidence;
your own acceptances and vetoes need the same proof as theirs. Two reviewers can
agree because they share the same mistaken premise.

Keep commit-message and grouping concerns in `Commit notes`; they need no
adjudication or pinning test and never affect the verdict. Set aside `Minor`
items without asking reviewers to revisit them. Fix one only when cheap and
another pass is already due. If a purported Minor item meets the finding
threshold, adjudicate it as a finding. If only Minor items and commit notes
remain, with no Open questions, the verdict is `LAND`.

For each remaining finding:

1. **Screen relevance.** Check the production trigger, effect, and recovery
   against the method's **Rate each defect** table before building a reproducer.
   Veto defects it drops. A defect the user explicitly asked to fix bypasses
   this rating, but still needs proof.
2. **Check scope.** Apply **Screen before building a reproducer** to every
   remaining finding, including Unexplained changes. If proving or fixing it
   needs work beyond the task or accepted plan, stop that work and record
   `Open`: trigger, effect, evidence, proved or suspected, estimated work,
   and the missing proof or user decision. Finish independent work within scope.
3. **Test the claim.** Run ground truth and the changed code on the same input.
   Accept when the comparison proves a bug. Veto when it proves the code right
   or the finding demands behavior no requirement specifies. If you cannot
   test the claim, leave it Open.
4. **Choose the remedy.** Use the smallest correct fix: every added line costs
   more to review, debug, and maintain. When several fixes are defensible and
   the requirements do not choose one, give the user the alternatives,
   tradeoffs, and your recommendation; wait for direction.

For an **Unexplained** change, answer the reviewer's question instead of
testing the claim:

- Veto if the answer already exists in the code, tests, documentation, or
  commit message; cite it.
- Otherwise accept and put the answer there, or simplify away the unexplained
  code. If you do not know the answer, trace the code within the scope check.
- Treat any defect uncovered during that investigation as a normal finding.

## 4. Pin, then fix

For each accepted fix within scope, add a pinning test using expected values
from ground truth. Include the command that produced them in the test comment.
Confirm the test fails before the fix, apply the fix, then run every affected
test. An Unexplained fix that changes no behavior needs no pinning test.

If proving or fixing the issue grows beyond scope, mark it `Open` and stop.
Accepting a diagnosis does not authorize extra implementation work.

## 5. Re-review in the same sessions

Follow **User direction** throughout. An Open question needing user direction
stops work and repeated review on that question. Finish independent authorized
fixes and tests, then report `REVISE`, the Open questions, and unreviewed changes.
Resume stopped work only after new evidence or user direction resolves it;
Open does not mean fixed or vetoed.

Otherwise, send adjudication to both reviewers even if every finding was vetoed
and no code changed. First pass all tests affected by fixes. Re-read the whole
current scope yourself and ask both reviewers to do the same:

```text
Re-read and re-review the complete current scope from the repository, then
return the normal verdict and findings. Do not rely on what you read last pass,
and do not limit the review to the fixes.

Author notes:
Accepted <ID>: <diagnosis, the fix and its location, how it was validated>
Vetoed <ID>: <evidence that the code is right or the reporting bar is not met>
Open <ID>: <proved or suspected, work stopped, cost, evidence or decision needed>

Files now in play: <updated file list, including files the fixes touched>
Proposed commit message: <current complete message>
Changed requirements or ground truth: <updates only, or "unchanged">

Keep existing finding IDs and give new issues new IDs. Report each prior
finding as resolved, still present, or disputed. If you think a veto is wrong,
say what evidence would settle it. Do not apply fixes, and do not ask the user
to adjudicate.
```

Use `none` for an empty list. Do not repaste requirements the session already
has. Include findings from your own read when they explain a fix.

Resume both reviewers using the exact recorded session IDs and the
[CLI protocol](references/reviewer-cli.md#resume-reviewers). It also defines
result validation and the fresh-session fallback when a session cannot resume.

Return to step 3 after each pass. Stop when:

- Both reviewers return `LAND` on the current tree and every finding is fixed,
  vetoed with evidence, or explicitly waived by the user. Record waivers as
  waivers, not fixes or disproof.
- You accept a `DISCARD`. Report it without reviewing that settled decision again.
- An Open question needs user direction, as described above.
- The review reaches four passes. Finish only fixes and tests within scope,
  then report the cap, unresolved findings, and unreviewed fixes.

A verdict does not cover later edits: re-review the full current scope unless
a stop rule applies. Skip re-review if the first pass raised no substantive
issue and no code changed. Minor items alone never cause another pass.

## 6. Report the verdicts

Report to the user and, when applicable, in the PR description:

1. One top-level `Verdict: LAND | REVISE | DISCARD` line. Open questions require
   `REVISE`.
2. The reviewed files, pass count, and both models' final verdicts, for example:
   `src/a.ts, src/a.spec.ts: 2 passes; Codex LAND, Claude LAND`.
   Only that model's CLI fills its slot. Otherwise state why it is missing,
   including any fallback result: `Claude missing (idle timeout)` or
   `Codex missing (CLI not installed; Claude subagent LAND)`.
3. Every substantive finding from all three reads, under its original ID,
   including accepted, vetoed, Open, and waived items. State unreviewed fixes
   separately. Omit Minor items. If there were no substantive findings or Open
   questions, report `LAND` and `No issues found.` without inventing rows.

Use this ledger; repeat the final verdict so copied rows retain their context:

| ID | Scope | Model | Finding and trigger | Disposition | Evidence (one line) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |

Add `Commit notes` only for warranted message or grouping improvements. Name the
model, explain why, and give the complete proposed message. For a split, name
each independently committable group and its message. These notes have no
severity and cannot change the verdict.

Follow the active plan's review-recording instructions. If it has none, record:

- While unfinished: reviewed files and pass count, reviewer CLIs and session IDs,
  and each finding's ID, disposition, and one line of evidence.
- When complete: each vetoed or waived claim with its evidence or user ruling,
  the final verdict and missing reviewer slots, and the reviewed base commit.

## Scratch files

Before making repository, build-output, or replay copies, read and follow the
shared [scratch-copy rules](../../references/scratch-files.md).

## Adapting for your project

- **Name the ground truth explicitly** — e.g. "the vendored reference
  implementation via `./third-party/tool/run`", "CPython 3.12 via
  `uv run python -c ...`", "the RFC's test vectors". Step 3 is only as strong as
  this.
- **Say how to name the diff range** the way your project talks about it — "the
  changes on this branch vs `develop`", "everything since the last tag".
- **Optional review focus** belongs in project guidance. Keep it a starting
  point; the reviewers still examine the full scope independently.
- **Name sandbox needs**: paths outside the repository that the project's tests
  write, and whether they need the network, so callers add them to the Codex
  commands.
- **Callers welcome**: other skills (`gitplan`, `tpp-orchestrate`) reference this
  file as their review gate. Keep the gate generic here; put workflow-specific
  bookkeeping (commit conventions, where the report goes) in the calling skill.
  What a plan document records about the review belongs to that plan's guide.
