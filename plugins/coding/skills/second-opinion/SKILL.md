---
name: second-opinion
description: Get a second opinion on freshly written code from the *other* coding agent — Claude asks Codex, Codex asks Claude — then empirically vet every finding against ground truth before accepting or vetoing it. Use when requested or as part of an active review workflow after tests pass. Do not trigger merely because the user instructs you to commit, or for a delegated review or finding-validation pass.
metadata:
  website: "https://photostructure.com/coding/claude-code-review/#second-opinion"
---

# Second Opinion

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

## Review workflow

Two reviews, from two different models, then evidence decides. You review the
code yourself — you know what the change was supposed to do. A *different* model
reviews it independently, with no access to your reasoning. Then every finding
from either pass is accepted or vetoed against ground truth.

Two failure modes motivate this:

1. **A green test suite is not proof of correctness.** Implementers satisfice:
   they code until *their own* tests pass. Semantic mismatches with the spec,
   stateful-API gotchas, and edge cases the tests never pin all survive.
2. **Reviewers are confidently wrong, too.** Every review pass mixes real bugs
   with plausible-but-wrong findings. Accepting blindly injects regressions;
   vetoing blindly ships the bugs.

A second opinion from the *same* model shares your blind spots. Cross-model is
the point: different training, different priors, different failure modes.

## Leaf-mode guard

If the task identifies your role as `leaf-reviewer` or sets
`delegation-budget: 0`, do not run this gate. Read and follow
[`../review/references/single-pass.md`](../review/references/single-pass.md),
complete one review yourself, return the report to the caller, and stop.

## 1. Scope the gate

Before launching anything, write down:

- **The diff range** — commit range, staged diff, or working-tree diff, plus the
  file list. Both reviews get exactly the same scope.
- **The substantive intent** — the task, accepted plan, specification excerpt, or
  change description that states what the content must do. Include a proposed
  Conventional Commit message when one exists, but label it as commit metadata,
  not a requirement. Do not draft a message merely to create a correctness
  boundary for the review.
- **Pasted context** — plan or TPP excerpts, settled decisions the reviewer must
  not re-litigate, and the project's own review exclusions. Paste their text
  into the prompt. A spawned CLI cannot chase references or basenames; anything
  absent from the prompt does not exist for it.
- **The ground truth** — the thing a disputed finding can be tested against: a
  reference implementation you can execute, a spec with runnable examples, the
  real API. Write the *exact command* to query it. No executable ground truth?
  Say so, and name the fallback (spec text, maintainer ruling).
- **A scrutiny list** — the 3-6 riskiest spots you'd check first: stateful APIs,
  encoding boundaries, off-by-one-prone length math, error paths, concurrency.
  It aims the reviewer without capping them.

## 2. Ask the other model

You know which model you are. Ask the other one.

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

Begin the prompt file with `$coding:review`; use `$coding:review-staged` instead
when the scope is the staged diff. Invoke plain `codex exec`, not
`codex exec review`: the `review` subcommand substitutes Codex's built-in review
prompt and cannot load this marketplace's skill. Name the diff range in the
prompt itself — "the uncommitted changes", "the changes since `<sha>`". Codex
needs the coding plugin installed:

```bash
codex plugin marketplace add photostructure/coding-skills
codex plugin add coding@photostructure
```

Do not pass `--ephemeral`: the session must remain resumable if fixes require
another review. `--output-last-message` captures the clean review while the
JSONL stream keeps the supervisor fed. After a clean exit, record the session
ID for the follow-up pass:

```bash
jq -r 'select(.type=="thread.started").thread_id' "<events-file>" | tail -n 1
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
Do not set it. Record the session ID for the follow-up pass:

```bash
jq -r 'if .type=="system" and .subtype=="init" then .session_id elif .type=="result" then .session_id else empty end' \
  "<events-file>" | tail -n 1
```

Begin the prompt file with `/coding:review`; use `/coding:review-staged` instead
when the scope is the staged diff. The `-p` prompt must begin with the slash
command so Claude invokes the skill directly. An unavailable slash command is a
plugin-loading failure even when Claude exits 0.

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

Construct the prompt file with all of the following:

- the review skill to follow: `coding:review` for a commit, range, or
  working-tree scope; `coding:review-staged` for the staged diff
- `role: leaf-reviewer` and `delegation-budget: 0`, so the named skill runs the
  shared single-pass method and returns one report without delegating, asking
  for adjudication, or entering a commit flow
- the diff scope, named in the prompt rather than only through CLI flags
- the substantive intent verbatim, with its source identified as the task,
  accepted plan, specification, or change description
- the proposed commit message verbatim as commit metadata, when one exists,
  with the instruction that message or grouping concerns belong only in a
  post-findings `Commit notes` section and cannot affect the verdict
- the pasted context and scrutiny list verbatim
- the ground truth and the exact command or procedure for querying it

Name the review skill; never name `second-opinion` in the reviewer prompt. The
reviewer must review the change, not recurse into another second opinion. If the
spawned CLI cannot load the coding plugin, rerun it with the full text of
[`../review/references/single-pass.md`](../review/references/single-pass.md)
pasted into the prompt instead of naming the review skill.

Resolve `<this-skill>` to this skill's directory. Run either command in the
background and poll the same job until it exits:

- **0** — read the review and record its session ID. A missing session ID does
  not invalidate this pass, but it requires the fresh-session fallback in the
  re-review loop.
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
  that retry fails, use the missing/unauthenticated fallback below. These are
  environment failures, not bugs in this skill.
- **0 with an `Unknown command`, a missing-skill result, or a final review that
  does not begin with the required LAND, REVISE, or DISCARD verdict** — the CLI
  did not run the shared method. Treat it as a plugin-loading failure, not a
  clean review, and use the pasted-method fallback below. Allow ordinary
  Markdown decoration around the verdict text.
- **any other non-zero** — report the status and finish your own pass.

**Read the new code yourself while the external review runs** — you are the
other reviewer, and the only one who knows the full context of what the change
was supposed to do.

Keep the two passes independent: give the external reviewer the scoped prompt
and repository state, never your suspected findings or interim conclusions.

If the other CLI is not installed or not authenticated, say so plainly and fall
back to a task-local subagent given
[`../review/references/single-pass.md`](../review/references/single-pass.md). A
same-model second opinion is weaker; report that you used one.

## 3. Vet every finding — accept and veto only with proof

First reclassify any concern that is only about the commit message or the
grouping, splitting, or ordering of otherwise-valid content. It is a commit
note, not a finding: do not accept or veto it, assign it a severity, or require a
pinning test. If these are the only concerns from both reviews, the verdict is
`LAND`.

For each finding from the external review and from your own read:

1. Construct the empirical test: run ground truth and the new code on the same
   input; compare. A finding you can't test this way gets downgraded to a
   question, not silently accepted.
2. **Accept** only when ground truth confirms the bug.
3. **Veto** only when ground truth confirms the code is right — or the finding
   demands fidelity nothing requires (e.g. mimicking a reference's internals on
   a path no contract pins).
4. When the diagnosis is right but the proposed fix is mediocre, take the better
   fix — reviewers identify problems; you own the remedy.

Reviewer confidence, eloquence, and *agreement between the two passes* are not
evidence. Two models converging on the same wrong finding is common; one command
against ground truth beats both.

Route the vet to the **authoring session** when one is resumable — its context
of settled decisions and corrected premises catches plausible-but-wrong
findings a fresh vetter cannot, and authors regularly (correctly) veto reviewer
findings for exactly that reason. An author's veto carries no special weight,
though: it needs the same recorded proof as anyone's, and whoever supervises
the gate audits veto evidence rather than trusting the author's stake in their
own code. Author context can also *contain* the defect — a wrong premise the
session has carried since birth — which is what the independent finder pass is
for.

## 4. Fix and pin

Apply accepted fixes. **Every accepted finding gets a pinning test** whose
expected values come from ground truth (paste the command that produced them
into the test's comment). The *full* suite must be green again — not just the
new tests.

## 5. Re-read and re-review after fixes

Continue this loop only while review remains in scope under **User direction**.

Any review-driven code edit can expose a new issue or introduce one. After the
fixes and full suite are green, re-read the complete current diff yourself and
ask the external reviewer to do the same. Do not limit either pass to checking
that the prior fixes worked.

Write a fresh follow-up prompt that:

- identifies the same diff scope, substantive intent, and ground truth;
- briefly lists the accepted fixes and the evidence for any vetoes, so the
  reviewer does not have to infer what changed or re-litigate settled facts;
- tells the reviewer to re-read every file in the current diff from the
  beginning, inspect interactions introduced by the fixes, look for issues the
  earlier pass missed, and return the normal `LAND`, `REVISE`, or `DISCARD`
  report; and
- retains `role: leaf-reviewer` and `delegation-budget: 0`.

Resume the recorded external session through the same idle-timeout supervisor.
For a Claude reviewer:

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
CLI cannot resume the recorded session, launch a fresh external session with
the complete original review prompt updated for the current diff, and disclose
that continuity was unavailable. A resume failure does not justify skipping
the re-review.

Vet every new finding, fix and pin accepted findings, and run the full suite
again. Repeat the re-read and resumed re-review after each batch of accepted
fixes. Stop when a complete post-fix pass produces no newly accepted findings,
or after three total external review passes. If the third pass produces an
accepted finding, fix and test it, but report that the external re-review cap
was reached rather than describing the result as a clean pass. Skip this loop
when neither review caused a code edit.

## 6. Report the verdicts

Summarize for the user (and for whatever plan/PR document tracks this work):
every substantive finding, accepted **and** vetoed, with one-line evidence for
each verdict, and which model raised it. Record vetoes especially — the next
session will rediscover the same "bug" and must not re-litigate it.

Use this compact ledger, repeating the final review verdict in each row so the
result remains legible when copied or aggregated:

Begin with one top-level `Verdict: LAND | REVISE | DISCARD` line. If no findings
survive, use `LAND`, follow it with `No issues found.`, and do not invent ledger
rows.

| Scope | Model | Finding | Severity | Accept/Veto | Evidence (one line) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |

After the ledger—or after `No issues found.` when there are no rows—add a brief
`Commit notes` section when either model proposed a warranted message or
grouping improvement. Name the model, state the specific reason, and give the
complete improved message. For a split, identify every independently
committable batch and give each batch's complete message. Keep these notes
outside the ledger; they have no severity and cannot change the verdict.

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
  `uv run python -c ...`", "the RFC's test vectors". The vetting step is only as
  strong as this.
- **Say how to name the diff range** the way your project talks about it — "the
  changes on this branch vs `develop`", "everything since the last tag".
- **Tune the scrutiny list** to your codebase's recurring failure modes and bake
  the worst offenders into this file.
- **Callers welcome**: other skills (`gitplan`, `tpp-orchestrate`) reference this
  file as their review gate. Keep the gate generic here; put workflow-specific
  bookkeeping (where verdicts get recorded, commit conventions) in the calling
  skill.
