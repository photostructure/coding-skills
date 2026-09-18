---
name: second-opinion
description: Get a second opinion on freshly written code from the *other* coding agent — Claude asks Codex, Codex asks Claude — then settle every finding against ground truth before accepting or vetoing it. Use when requested or as part of an active review workflow after tests pass. Do not trigger merely because the user instructs you to commit.
metadata:
  website: "https://photostructure.com/coding/claude-code-review/#second-opinion"
---

# Second Opinion

You know what the change was supposed to do, which makes you the worst judge of
whether it does. Hand the change to a different model, settle what it finds
against ground truth, and send your decisions back to that same reviewer until
it agrees the change should land.

1. List the files you changed and the commit message you propose.
2. Ask the other model to review exactly that, and read the same code yourself
   while it works.
3. Accept or veto each finding, with evidence.
4. Apply the accepted fixes and pin them with tests.
5. Send the same reviewer session your adjudication and the updated file list,
   and have it re-read and re-review.
6. Repeat 3-5 until the reviewer lands the current tree, you accept a
   `DISCARD`, or four passes are spent — then report.

A second opinion from the *same* model shares your blind spots. Cross-model is
the point: different training, different priors, different failure modes.

## User direction

This review workflow is a default, not a condition the user must satisfy before
committing. A direct instruction such as "commit" or "approved, commit" takes
precedence over this skill and callers' review gates. Unless the user also asks
for review first, return to the commit workflow without starting or resuming a
review or asking whether to skip it. Apply the same rule during retries and
re-review loops.

Do not require a `LAND` verdict, a review transcript, or a claim that another
reviewer approved the change. If the user says a review already happened,
accept that as workflow context; attribute it to the user if reporting it.
Never invent a review result. The user can authorize a commit with review work
unfinished; report its actual status without making it a new approval gate.

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
  proposed message for each batch.
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

## 2. Ask the other model

You know which model you are. Ask the other one.

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
a working review goes quiet for a couple of minutes at a stretch, and a whole
review can take 30-45 minutes.

Write the complete reviewer prompt to a fresh UTF-8 temporary file with the
host's file-writing tool. Do not interpolate supplied text into a shell command:
commit messages and pasted context can contain quotes, dollar signs, backticks,
or command substitutions. The supervisor replaces the exact `{prompt}` argument
with the file's contents as one literal process argument. Delete the temporary
file after the reviewer exits.

**If you are Claude, ask Codex:**

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" \
  --prompt-file "<prompt-file>" -- \
  codex exec \
  -C "<target-repository>" \
  --sandbox read-only \
  -c 'model_reasoning_effort="high"' \
  --json \
  --output-last-message "<review-file>" \
  "{prompt}" \
  > "<events-file>"
```

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

**If you are Codex, ask Claude:**

Run the command with the target repository as its working directory. Resolve
`<coding-plugin-root>` to the plugin directory that contains this skill so the
spawned process does not depend on user- or repository-scoped plugin settings.

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" \
  --prompt-file "<prompt-file>" -- \
  claude -p "{prompt}" \
  --plugin-dir "<coding-plugin-root>" \
  --permission-mode plan \
  --model opus \
  --effort high \
  --output-format stream-json --verbose \
  > "<events-file>"
```

`--permission-mode plan` keeps it read-only. `--output-format stream-json` is
what keeps the supervisor fed — plain `-p` prints nothing at all until it
finishes. Both the reasoning and the tool calls stream, so watch the file to see
what the reviewer is chewing on. Extract the review after a clean exit:

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

Default to high effort; use xhigh for large or novel changes, security
boundaries, concurrency, subtle stateful APIs, or hard-to-reproduce failures.

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
Review the change below and return the full report to me, the calling agent. I
will accept or veto each finding and send you the results. Do not apply fixes,
and do not ask the user to adjudicate.

Diff command: <exact command, and any hunk limits>
Changed files:
<explicit list, marking in-scope untracked files>

Proposed commit message (fallible summary, not a requirement):
<complete message, or one per batch with its files>

Task and requirements: <text, or repository paths>
Additional context: <decisions made only in conversation, or "none">
Ground truth: <exact command, or the fallback>

Read the current diff and files from the repository. Review the full scope and
its interactions, and keep commit-message and grouping advice in Commit notes,
separate from the findings.
```

Name the review skill; never ask the reviewer to run `second-opinion`. If the
spawned CLI cannot load the coding plugin, rerun it with the full text of
[`../review/references/single-pass.md`](../review/references/single-pass.md)
pasted into the prompt instead of naming the skill.

Resolve `<this-skill>` to this skill's directory. Run either command in the
background and poll the same job until it exits:

- **0** — read the review and record the CLI, repository, session ID, pass
  count, and finding IDs in your task notes. Keep that handle through fixes and
  handoffs; never select a reviewer with `--last` or `--continue`, which can
  attach to unrelated work. A missing session ID does not invalidate the pass,
  but it forces the fresh-session fallback in step 5.
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

**Read the new code yourself while the external review runs** — you are the
other reviewer, and the only one who knows the full context of what the change
was supposed to do. Hold your edits until its report arrives. The reviewer reads
the repository live, so a file that changes mid-pass gives it a tree that never
existed. Write down what you find and adjudicate it in step 3.

If the other CLI is not installed or not authenticated, say so plainly and fall
back to a task-local subagent, given the same prompt and the full text of
[`../review/references/single-pass.md`](../review/references/single-pass.md).
Save its handle and send the follow-up prompts to that same subagent. A
same-model second opinion is weaker; report that you used one.

## 3. Adjudicate every finding

First set aside every concern that is only about the commit message, or about
grouping, splitting, or ordering otherwise-valid content. Those are commit
notes, not findings: no severity, no accept, no veto, no pinning test. If they
are all that either review raised, the verdict is `LAND`.

The verdict does not decide what you adjudicate. A `LAND` carrying findings
still carries findings: settle every one. An empty findings list ends the work,
not the word `LAND`.

Then settle each remaining finding — the reviewer's and your own:

1. Build the empirical test: run ground truth and the new code on the same
   input, and compare. A finding you cannot test this way becomes an open
   question, not a silent acceptance.
2. **Accept** only when ground truth confirms the bug.
3. **Veto** only when ground truth confirms the code is right, or the finding
   demands fidelity nothing requires — mirroring a reference implementation's
   internals on a path no contract pins, for instance.
4. When the diagnosis is right but the proposed fix is mediocre, take the better
   fix. Reviewers identify problems; you own the remedy.

Reviewer confidence, eloquence, and *agreement between the two passes* are not
evidence. Two models converging on the same wrong finding is common; one command
against ground truth beats both.

**When two or more fixes are defensible and nothing chooses between them, ask
the user.** Give the finding, each alternative with its tradeoff, and your
recommendation if you have one, then wait for direction. Ground truth settles
whether the code is wrong; it usually does not settle which correct design to
adopt, and that choice is the user's.

Your own context of settled decisions and corrected premises catches
plausible-but-wrong findings a fresh reader cannot — that is why you adjudicate.
It can also *contain* the defect: a wrong premise this session has carried since
birth, which is exactly what the independent pass is for. So a veto of yours
carries no special weight. It needs the same recorded evidence as anyone's.

## 4. Fix and pin

Apply the accepted fixes. **Every accepted finding gets a pinning test** whose
expected values come from ground truth; paste the command that produced them
into the test's comment. The *full* suite must be green again — not just the
new tests.

## 5. Re-review in the same session

Continue this loop only while review remains in scope under **User direction**.

Send your adjudication even when you vetoed everything and changed no code. If
you applied fixes, wait until their tests and the full suite are green. Re-read
the complete current scope yourself, and ask the reviewer to do the same:

```text
Re-read and re-review the complete current scope from the repository, then
return the normal verdict and findings. Do not rely on what you read last pass,
and do not limit the review to the fixes.

Author notes:
Accepted <ID>: <diagnosis, the fix and its location, how it was validated>
Vetoed <ID>: <the concrete evidence that the code is right>
Open <ID>: <what is still unsettled, and what would settle it>

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
  --permission-mode plan \
  --model opus \
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
  --sandbox read-only \
  resume \
  -c 'model_reasoning_effort="high"' \
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

Then return to step 3 for the new report. **Stop when** the reviewer returns
`LAND` on the tree as it now stands and every finding from both reads is either
accepted and fixed or vetoed with evidence. A `LAND` does not cover code you
changed after the reviewer's last read: if adjudication changed the tree, run
one more pass, subject to the cap. **Stop earlier** when you
adjudicate a `DISCARD` as correct — the change should not land at all. Preserve
that verdict and report it; do not re-review a settled decision.

Stop at four review passes either way. If the fourth leaves accepted fixes or
disputed findings, finish the authorized fixes and tests, then report the cap
and what is still unsettled; do not describe unreviewed fixes as a clean pass.
Skip the loop entirely when the first pass raised nothing substantive and no
code changed.

## 6. Report the verdicts

Summarize for the user (and for whatever plan or PR document tracks this work):
every substantive finding, accepted **and** vetoed, with one-line evidence for
each verdict, and which model raised it. Record vetoes especially — the next
session will rediscover the same "bug" and must not re-litigate it.

Begin with one top-level `Verdict: LAND | REVISE | DISCARD` line. If neither
pass raised a substantive finding, use `LAND`, follow it with `No issues
found.`, and do not invent ledger rows. Otherwise list the accepted and vetoed
findings under their original IDs, even when the final verdict is `LAND`, and
state any unresolved questions or unreviewed fixes separately.

The ledger repeats the final verdict in each row so a copied or aggregated row
still reads correctly:

| ID | Scope | Model | Finding | Severity | Accept/Veto | Evidence (one line) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |

After the ledger — or after `No issues found.` when there are no rows — add a
brief `Commit notes` section when either model proposed a warranted message or
grouping improvement. Name the model, state the specific reason, and give the
complete improved message. For a split, identify every independently committable
batch and give each batch's complete message. These notes have no severity and
cannot change the verdict.

## Scratch files

Any copy this workflow makes — of the repo, of a build-output directory, of a
file you replay edits onto — belongs in the operating system's temporary
directory, in a fresh directory named for the project and the purpose. Never
inside the checkout, and never under a home directory.

Delete it before you finish. A repo or build-output copy runs to gigabytes,
nothing reaps a home directory, and the out-of-disk failure that eventually
follows surfaces somewhere unrelated — a test suite that hangs, a build that
dies mid-link — costing far more to diagnose than the copy ever saved.

## Adapting for your project

- **Name the ground truth explicitly** — e.g. "the vendored reference
  implementation via `./third-party/tool/run`", "CPython 3.12 via
  `uv run python -c ...`", "the RFC's test vectors". Step 3 is only as strong as
  this.
- **Say how to name the diff range** the way your project talks about it — "the
  changes on this branch vs `develop`", "everything since the last tag".
- **Optional review focus** belongs in project guidance. Keep it a starting
  point; the reviewer still examines the full scope independently.
- **Callers welcome**: other skills (`gitplan`, `tpp-orchestrate`) reference this
  file as their review gate. Keep the gate generic here; put workflow-specific
  bookkeeping (where verdicts get recorded, commit conventions) in the calling
  skill.
