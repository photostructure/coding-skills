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

**If you are Claude, ask Codex:**

```bash
codex exec review --base main "<scope, ground truth, scrutiny list, and: report only issues you can prove, with file:line and a concrete failing scenario; say 'No issues found' rather than padding>"
```

Use `--commit <sha>` for a commit you already made, or `--uncommitted` for
working-tree and staged changes. `codex exec review` is read-only and
non-interactive.

**If you are Codex, ask Claude:**

```bash
claude -p "<same prompt>" --permission-mode plan
```

`--permission-mode plan` keeps it read-only. Add `--model opus` for large,
novel, or security-sensitive work.

Start the review in the background if your host supports it, and **read the new
code yourself while it runs** — you are the other reviewer, and the only one who
knows the full context of what the change was supposed to do.

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
- **Pin the base branch** in the `codex exec review --base` example if yours
  isn't `main`.
- **Tune the scrutiny list** to your codebase's recurring failure modes and bake
  the worst offenders into this file.
- **Callers welcome**: other skills (`gitplan`, `tpp-orchestrate`) reference this
  file as their review gate. Keep the gate generic here; put workflow-specific
  bookkeeping (where verdicts get recorded, commit conventions) in the calling
  skill.
