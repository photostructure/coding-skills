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
- **The claimed intent** — the proposed Conventional Commit message for the
  change. Draft one first if it does not exist; without it, the reviewer cannot
  ask whether the diff delivers exactly what the message claims, no more and no
  less.
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
  --ephemeral \
  -c 'model_reasoning_effort="high"' \
  "{prompt}" \
  > "<review-file>"
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

Codex sends progress to stderr and its final review to stdout, so the redirect
captures a clean review while the stream stays watchable.

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

Begin the prompt file with `/coding:review`; use `/coding:review-staged` instead
when the scope is the staged diff. The `-p` prompt must begin with the slash
command so Claude invokes the skill directly. An unavailable slash command is a
plugin-loading failure even when Claude exits 0.

Default to high effort; use xhigh for large or novel changes, security
boundaries, concurrency, subtle stateful APIs, or hard-to-reproduce failures.

The command shapes above were empirically validated against a tiny committed
repository with Claude Code 2.1.222 and `codex-cli` 0.146.1. Do not substitute a
similarly named built-in review mode without re-validating it against a real
diff.

Construct the prompt file with all of the following:

- the review skill to follow: `coding:review` for a commit, range, or
  working-tree scope; `coding:review-staged` for the staged diff
- `role: leaf-reviewer` and `delegation-budget: 0`, so the named skill runs the
  shared single-pass method and returns one report without delegating, asking
  for adjudication, or entering a commit flow
- the diff scope, named in the prompt rather than only through CLI flags
- the proposed commit message verbatim as the claimed intent, with the
  instruction that any diff-versus-message mismatch is a High finding
- the pasted context and scrutiny list verbatim
- the ground truth and the exact command or procedure for querying it

Name the review skill; never name `second-opinion` in the reviewer prompt. The
reviewer must review the change, not recurse into another second opinion. If the
spawned CLI cannot load the coding plugin, rerun it with the full text of
[`../review/references/single-pass.md`](../review/references/single-pass.md)
pasted into the prompt instead of naming the review skill.

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
- **0 with an `Unknown command` or missing-skill result** — the CLI did not load
  the plugin. Treat it as a plugin-loading failure, not a clean review, and use
  the pasted-method fallback below.
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

Use this compact ledger, repeating the final review verdict in each row so the
result remains legible when copied or aggregated:

Begin with one top-level `Verdict: LAND | REVISE | DISCARD` line. If no findings
survive, follow it with `No issues found.` and do not invent ledger rows.

| Scope | Model | Finding | Severity | Accept/Veto | Evidence (one line) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |

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
