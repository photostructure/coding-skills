---
name: second-opinion
description: Get a second opinion on freshly written code from the *other* coding agent — Claude asks Codex, Codex asks Claude — then empirically vet every finding against ground truth before accepting or vetoing it. Use once the code is written and the tests pass, before you commit. Do not use for a delegated review or finding-validation pass.
---

# Second Opinion

> Documented in depth: [Most AI code reviews are noise. Here's how to fix that.](https://photostructure.com/coding/claude-code-review/)

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

**If you are Claude, ask Codex:**

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" -- \
  codex exec \
  -C "<target-repository>" \
  --sandbox read-only \
  --ephemeral \
  -c 'model_reasoning_effort="high"' \
  review "<same prompt>" \
  > "<review-file>"
```

Name the diff range in the prompt itself — "the uncommitted changes", "the
changes since `<sha>`". Do **not** reach for `--base`, `--commit`, or
`--uncommitted`: each is mutually exclusive with a custom prompt, so adding one
kills the run in milliseconds with exit 2 and your scrutiny list never arrives.
Codex sends progress to stderr and its final review to stdout, so the redirect
captures a clean review while the stream stays watchable.

**If you are Codex, ask Claude:**

```bash
python3 "<this-skill>/scripts/run_with_idle_timeout.py" -- \
  claude -p "<same prompt>" \
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

Default to high effort; use xhigh for large or novel changes, security
boundaries, concurrency, subtle stateful APIs, or hard-to-reproduce failures.

Resolve `<this-skill>` to this skill's directory. Run either command in the
background and poll the same job until it exits:

- **0** — read the review.
- **124 with the supervisor's `idle timeout:` diagnostic** — the reviewer went
  silent for 15 minutes. Discard the partial review, say so, and finish your own
  pass.
- **124 without that diagnostic** — the reviewer CLI itself returned 124.
  Report its status and finish your own pass; do not call it an idle timeout.
- **a fast non-zero with a CLI usage or unknown-option diagnostic** — the
  invocation is stale. Report it as a bug in this skill; never let it pass as
  "no issues found".
- **127 or an authentication error** — use the missing/unauthenticated fallback
  below. These are environment failures, not bugs in this skill.
- **any other non-zero** — report the status and finish your own pass.

**Read the new code yourself while the external review runs** — you are the
other reviewer, and the only one who knows the full context of what the change
was supposed to do.

Keep the two passes independent: give the external reviewer the scoped prompt
and repository state, never your suspected findings or interim conclusions.

Whichever CLI you invoke, pass the scope and expectations in the prompt, not the
name of this skill or any other workflow skill. If the other CLI is not
installed or not authenticated, say so plainly and fall back to a task-local
subagent given
[`../review/references/single-pass.md`](../review/references/single-pass.md). A
same-model second opinion is weaker; report that you used one.

## 3. Vet every finding — accept and veto only with proof

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

## 4. Fix and pin

Apply accepted fixes. **Every accepted finding gets a pinning test** whose
expected values come from ground truth (paste the command that produced them
into the test's comment). The *full* suite must be green again — not just the
new tests.

## 5. Report the verdicts

Summarize for the user (and for whatever plan/PR document tracks this work):
every finding, accepted **and** vetoed, with one-line evidence for each verdict,
and which model raised it. Record vetoes especially — the next session will
rediscover the same "bug" and must not re-litigate it.

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
