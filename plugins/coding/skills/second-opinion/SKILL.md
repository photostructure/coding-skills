---
name: second-opinion
description: Get second opinions on freshly written code from fresh Codex and Claude reviewers, then settle every finding against ground truth before accepting or vetoing it. Use when requested, when project instructions require review before commits, or as part of an active review workflow after tests pass.
metadata:
  website: "https://photostructure.com/coding/claude-code-review/#second-opinion"
---

# Second Opinion

You know what the change was supposed to do, which makes you the worst judge of
whether it does. Give fresh Codex and Claude sessions the complete requested
review scope, then settle their findings against evidence. Do not split agent
reviews to meet a line count or reading-time budget; those limits belong to
human gavel reviews. Fresh reviewers can challenge assumptions the author's
session has accumulated.

1. Prepare the scope, proposed commit message, requirements, and ground truth.
2. Run both reviewers and read the same code yourself.
3. Accept, veto, or leave open each finding, with evidence.
4. Test and fix accepted findings within scope.
5. Re-review in the same sessions, subject to the stop rules in step 5.
6. Report findings, dispositions, and both reviewers' verdicts.

## User direction

"Commit now" and similar instructions to commit now end the review: stop any
reviewers still running, do not start or resume one, and commit. "Commit when
ready" and similar instructions mean finish the review first, then commit
without asking for approval again. The user's wording decides this even when
project instructions require review before every commit.

Without either instruction, follow project instructions: if they require
review before every commit, finish reviewing the current changes unless the
user explicitly says to skip review.

An Open item, whether work stopped at the scope check or a claim nobody could
test, is not a finished review: report it and wait for the user, even after
"commit when ready".

Accept the user's statement that review already happened; attribute it to them
when reporting it. Do not demand a transcript or `LAND`, invent a review result,
or turn unfinished review into a new gate after the user authorizes committing;
report its actual status instead.

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

Run both commands below at the same time on the complete review scope. Whichever
model you are, the reviewer from your own model is a fresh process with none of
this session's context. Both reviewers share the working tree, so reproduce any
build or test failure they report before accepting it: the other reviewer's
concurrent run may have caused it.

Honor standing review authorization in the user's global or project
instructions, including its repository scope and permitted providers. When a
sandbox escalation needs approval, cite that authorization's source and exact
wording in the request, along with the review scope and destination. A saved
memory that has not been read is not evidence available to the approval
reviewer. Do not ask the user to repeat authorization that already covers the
action. This skill does not itself grant permission to disclose code, and
standing authorization does not override a host-policy denial.

Both commands run under a supervisor that kills the reviewer after 15 minutes of
silence and reaps its whole process group. The window is deliberately generous:
a working review goes quiet for a couple of minutes at a stretch, and a review
can run a slow build or test suite.

Write the complete reviewer prompt to a fresh UTF-8 temporary file with the
host's file-writing tool. Do not interpolate supplied text into a shell command:
commit messages and pasted context can contain quotes, dollar signs, backticks,
or command substitutions. The supervisor replaces the exact `{prompt}` argument
with the file's contents as one literal process argument. Delete the temporary
file after the reviewer exits.

**The Codex reviewer:**

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" \
  --prompt-file "<prompt-file>" -- \
  codex exec \
  -C "<target-repository>" \
  --sandbox workspace-write \
  -m gpt-6.1-sol \
  -c 'model_reasoning_effort="xhigh"' \
  --json \
  --output-last-message "<review-file>" \
  "{prompt}" \
  > "<events-file>"
```

`workspace-write` lets the reviewer run the project's typecheck, build, and
tests to prove a finding. It can write inside the repository and the temporary
directory; every other path is read-only and the network is off. When the
project's tests write elsewhere or need the network, add
`-c 'sandbox_workspace_write.writable_roots=["<path>"]'` or
`-c 'sandbox_workspace_write.network_access=true'` to both Codex commands, as
the project's guidance directs.

Begin the prompt file with `$coding:review`, including for a staged diff.
Invoke plain `codex exec`, not the `review` subcommand: that substitutes
Codex's built-in review prompt and cannot load this marketplace's skill. Name
the diff range in the prompt itself — "the uncommitted changes", "the changes
since `<sha>`". Codex needs the coding plugin installed:

```bash
codex plugin marketplace add photostructure/coding-skills
codex plugin add coding@photostructure
```

Do not pass `--ephemeral`: the session must remain resumable for the re-review.
`--output-last-message` captures the clean review while the JSONL stream keeps
the supervisor fed. After a clean exit, record the session ID:

```bash
jq -sr '[.[] | select(.type=="thread.started") | .thread_id] | last // empty' "<events-file>"
```

**The Claude reviewer:**

Run the command with the target repository as its working directory. Resolve
`<coding-plugin-root>` to the plugin directory that contains this skill so the
spawned process does not depend on user- or repository-scoped plugin settings.

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" \
  --prompt-file "<prompt-file>" -- \
  claude -p "{prompt}" \
  --plugin-dir "<coding-plugin-root>" \
  --permission-mode auto \
  --disallowedTools Edit Write NotebookEdit \
  --model claude-opus-5-5 \
  --effort high \
  --output-format stream-json --verbose \
  > "<events-file>"
```

`--permission-mode auto` lets the reviewer run the project's typecheck, build,
and tests, with Claude Code's classifier refusing risky commands.
`--disallowedTools` removes the file-editing tools. `--output-format
stream-json` is what keeps the supervisor fed — plain `-p` prints nothing at all
until it finishes. Both the reasoning and the tool calls stream, so watch the
file to see what the reviewer is chewing on. Extract the review after a clean
exit:

```bash
jq -r 'select(.type=="result").result' "<events-file>"
```

Claude persists print-mode sessions unless `--no-session-persistence` is set.
Do not set it. Record the session ID:

```bash
jq -sr '[.[] | select((.type=="system" and .subtype=="init") or .type=="result") | .session_id // empty] | last // empty' \
  "<events-file>"
```

Begin the prompt file with `/coding:review`, including for a staged diff. The
`-p` prompt must begin with the slash command so Claude invokes the skill
directly. An unavailable slash command is a plugin-loading failure even when
Claude exits 0.

**You MUST set the model and effort on every reviewer launch and every resume.**
Pass `-m gpt-6.1-sol -c 'model_reasoning_effort="xhigh"'` to every `codex exec`
command and `--model claude-opus-5-5 --effort high` to every `claude -p`
command, exactly as shown. Never drop or change these flags when you rewrite,
retry, shorten, or resume a command. Without `-m`, Codex runs whatever `model`
the user's Codex config holds at that moment, which the Codex app can change;
review runs that omitted it ran on `gpt-6-astra` and spent most of a week's
Codex quota. If a CLI rejects the model name, report the error and mark that
model's slot missing; never rerun without the flag or with another model.
On a Codex host, a reviewer you start with `spawn_agent` instead of a CLI, such
as the fallback below, MUST pass `model: "gpt-6.1-sol"` and
`reasoning_effort: "xhigh"`; without them it inherits this session's model and
effort, whatever those are.

Claude.ai OAuth may need to rewrite its credential store when refreshing an
expired token. On Codex hosts whose filesystem sandbox can read but not write
`~/.claude`, the command may return an expired-token 401 even though
`claude auth status` reports logged in or the same command works in the user's
terminal. In that specific case, retry the exact supervised command once with
the host's narrow filesystem-sandbox escalation (`sandbox_permissions:
require_escalated` where available) so Claude can refresh its existing
credential. Do not read, print, copy, or manually rewrite the credential. If
the escalated retry fails, use the unauthenticated fallback below.

These command shapes depend on Claude print-session persistence and `--resume`,
and on Codex JSON events, `--output-last-message`, and `exec resume`. Revalidate
them against a real diff when those CLI options change. Do not substitute a
similarly named built-in review mode without the same validation.

After the skill invocation, the prompt file carries the step 1 inputs:

```text
Review the scope below and return the full report to me, the calling agent. I
will accept or veto each finding and send you the results. Do not apply fixes,
and do not ask the user to adjudicate.

Diff command: <exact command, and any hunk limits>
Changed files:
<explicit list, marking in-scope untracked files>

Proposed commit message (fallible summary, not a requirement):
<complete message, or one per commit with its files>

Task and requirements: <text, or repository paths>
Additional context: <decisions made only in conversation, or "none">
Ground truth: <exact command, or the fallback>

Read the current diff and files from the repository. Review the full scope and
its interactions, and keep commit-message and grouping advice in Commit notes,
separate from the findings. You may run the project's typecheck, build, and
tests, or a reproducer in the temporary directory, to prove a finding. Do not
edit tracked files. Another reviewer is reviewing this checkout at the same
time and may build and test too: follow the project's shared-checkout rules,
do not clean or delete shared build outputs while another run may be using
them, and rerun any failure a concurrent run could explain before reporting it.
```

Name the review skill; never ask the reviewer to run `second-opinion`. If the
spawned CLI cannot load the coding plugin, rerun it with the full text of
[`../review/references/single-pass.md`](../review/references/single-pass.md)
pasted into the prompt instead of naming the skill.

Resolve `<this-skill>` to this skill's directory. Run both commands in the
background and poll each job until it exits:

- **0** — read the review and record the CLI, repository, review scope, session ID,
  pass count, and finding IDs in your task notes. Keep that handle through fixes
  and handoffs (step 6 says what a plan carries across one); never select a
  reviewer with `--last` or `--continue`, which can attach to unrelated work. A
  missing session ID does not invalidate the pass, but it forces the
  fresh-session fallback in step 5.
- **124 with the supervisor's `idle timeout:` diagnostic** — the reviewer went
  silent for 15 minutes. Discard the partial review, say so, and finish your own
  pass.
- **124 without that diagnostic** — the reviewer CLI itself returned 124.
  Report its status and finish your own pass; do not call it an idle timeout.
- **a fast non-zero with a CLI usage or unknown-option diagnostic** — the
  invocation is stale. Report it as a bug in this skill; never let it pass as
  "no issues found".
- **127 or an authentication error** — for an expired Claude.ai OAuth error
  from Codex, use the one-time sandbox-escalation retry above. Otherwise, or if
  that retry fails, use the fallback below. These are environment failures, not
  bugs in this skill.
- **0 with an `Unknown command`, a missing-skill result, or a final review that
  does not begin with the required LAND, REVISE, or DISCARD verdict** — the CLI
  did not run the shared method. Treat it as a plugin-loading failure, not a
  clean review, and use the pasted-method fallback above. Allow ordinary
  Markdown decoration around the verdict text.
- **any other non-zero** — report the status and finish your own pass.

**Read the new code yourself while the reviewers run** — you are the third
reviewer, and the only one who knows the full context of what the change was
supposed to do. Hold your edits until both reports arrive. The reviewers read
the repository live, so a file that changes mid-pass gives them a tree that
never existed. Write down what you find and adjudicate it in step 3.

If either CLI is not installed or not authenticated, say so plainly and run
that reviewer as a task-local subagent of a model you can reach, given the same
prompt and the full text of
[`../review/references/single-pass.md`](../review/references/single-pass.md).
Save its handle and send the follow-up prompts to that same subagent. Its
findings count, but its verdict is not that model's verdict: the step 6 report
marks that model's slot as missing.

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

Resume the recorded session in the same repository, through the same supervisor,
with its exact session ID. Do not fork it or start a new session for an ordinary
follow-up. For a Claude reviewer:

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" \
  --prompt-file "<follow-up-prompt-file>" -- \
  claude -p "{prompt}" \
  --resume "<session-id>" \
  --plugin-dir "<coding-plugin-root>" \
  --permission-mode auto \
  --disallowedTools Edit Write NotebookEdit \
  --model claude-opus-5-5 \
  --effort high \
  --output-format stream-json --verbose \
  > "<next-events-file>"
```

For a Codex reviewer:

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" \
  --prompt-file "<follow-up-prompt-file>" -- \
  codex exec \
  -C "<target-repository>" \
  --sandbox workspace-write \
  resume \
  -m gpt-6.1-sol \
  -c 'model_reasoning_effort="xhigh"' \
  --json \
  --output-last-message "<next-review-file>" \
  "<session-id>" \
  "{prompt}" \
  > "<next-events-file>"
```

Apply the same exit-status and output-validity checks as the first pass. If the
CLI cannot resume the recorded session, launch a fresh one with the original
prompt updated for the current scope, plus the prior report, its finding IDs,
and every accept and veto with its evidence. Record the replacement handle and
disclose that continuity was unavailable. A resume failure does not justify
skipping the re-review.

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

Put repository, build-output, and replay copies in a fresh directory under the
operating system's temporary directory, named for the project and purpose.
Never put them in the checkout or home directory. Delete them before finishing.
Abandoned repository and build copies can consume gigabytes and cause unrelated
failures when the disk fills.

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
