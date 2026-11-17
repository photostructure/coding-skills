---
name: tpp-orchestrate
description: Work through a queue of Technical Project Plans serially — delegate each to a TDD subagent, get a cross-model second opinion, empirically vet every finding, and make one coherent commit per plan. Use when executing a documented plan queue such as _todo/ or _feat-name/ for a port, migration, or multi-stage feature.
metadata:
  website: "https://photostructure.com/coding/claude-code-tpp/#tpp-orchestrate-drive-a-queue"
---

# TPP Orchestration

Execute a documented queue of Technical Project Plans (TPPs), using its roadmap
or `README.md` for dependency order. The queue may be a backlog such as `_todo/`
or a feature integration queue such as `_feat-auth/`.

Read the project's `docs/TPP-GUIDE.md` when present; otherwise use the bundled
[TPP-GUIDE.md](../tpp/TPP-GUIDE.md). The guide owns plan layout and lifecycle;
[second-opinion](../second-opinion/SKILL.md) owns the review gate. This skill
owns delegation, queue order, recording, and one commit per completed plan.
Use [tpp](../tpp/SKILL.md) to work one plan directly and
[handoff](../handoff/SKILL.md) to leave unfinished work ready to resume.

## User direction

A request to execute this queue includes the one commit per completed TPP in
step 6. Do not ask again for those commits.
Read and follow the shared [commit instructions](../../references/howto-commit.md).

An instruction about the current commit does not waive reviews for later TPPs.
Do not mark unfinished implementation or acceptance criteria done.

## Before the first TPP

- Read the roadmap and every queued TPP's summary. Confirm dependency order.
- Identify the project's **ground truth** as the gate defines it, and write down
  the exact command to query it. Every TPP in the queue is vetted against it.
- Ask the user any clarifying questions **now** — scope ambiguities are cheapest
  to resolve before any code exists.

The run is finished when every queued TPP is in `_done/` with its commit and the
roadmap's status section matches.

## When to stop

Move from one step, and one TPP, to the next without checking in. Put status
notes in the same message as your next action. Stop the queue and ask the user
only when:

- a question would change what the TPP builds (steps 1 and 3);
- the review gate ends without both reviewers landing the current scope,
  because its four passes are spent, you accepted a `DISCARD`, or an Open
  question needs user direction;
- ground truth contradicts the TPP;
- the next action deletes data, force-pushes, or changes anything outside the
  repository.

## The loop, per TPP

Work **serially**: one TPP through the full loop before starting the next. Only parallelize TPPs within a wave when their file sets are provably disjoint _and_ neither depends on the other's decisions — review gates stay per-TPP either way.

### 1. Scope and clarify

Read the TPP and its sources of truth. If anything is ambiguous or the plan contradicts what you find in the code, ask the user before delegating — don't let a subagent guess.

### 2. Delegate with TDD

Launch an implementation subagent through the host's available collaboration
mechanism. Select the strongest available model and higher reasoning effort for
large, novel, security-sensitive, or weakly specified work. Use a faster model
or moderate reasoning effort only when the TPP, reference behavior, and existing
tests pin the implementation tightly. If the surface does not expose model
selection, keep the same risk-based scrutiny in the prompt and review gate.

The prompt must include:

- The TPP path and the sources of truth (spec files, reference implementation paths).
- **Tests first**: port or write the acceptance tests, run them and confirm they fail, then implement until they pass. Every test the change could affect must pass too, not just the new ones.
- Project pitfalls relevant to this TPP (from `AGENTS.md`, optional
  `CLAUDE.md`, or the TPP itself).
- "You cannot talk to the user. Record open questions, assumptions you made, and every intentional divergence from the plan in your final report."

### 3. Relay questions

Triage the subagent's open questions. Ask the user about decision-worthy ones
**before** the review gate — a review of code built on a wrong assumption is
wasted.

### 4. Run the review gate

Read and follow [../second-opinion/SKILL.md](../second-opinion/SKILL.md) on this
TPP's diff. The gate owns reviewer creation, adjudication, and pinning tests —
do not add reviewers here or restate its rules. Give it what its first step asks
for: the changed files and diff range, the proposed commit message, this TPP's
spec and reference paths, and the ground-truth command. Keep your own suspicions
out of it; the gate's reviewers read the code independently.

You are the gate's third reviewer, and the only one who knows the whole roadmap.
Read the new code yourself while the reviewers run.

If the review stops with Open questions needing user direction, report them
and wait before closing this TPP. Resume only after that direction or new
evidence resolves them; do not restart the stopped work to obtain `LAND`.

### 5. Record the verdicts

Report every finding, including Open questions and user waivers, in the per-TPP
summary to the user, with the evidence for each disposition and which model
raised it. Record the review in the TPP's **Working log**, as TPP-GUIDE's
**Keeping TPPs useful** section describes; step 6 moves what lasts out of it.

### 6. Close out

Move what lasts out of the TPP's Working log as TPP-GUIDE describes, delete the
log, move the TPP to `_done/`, update the roadmap's status section, and make **one coherent commit per TPP** (implementation + tests + TPP move together), following the repo's commit conventions. Then start the next TPP.

## Guidelines

- **Run the review gate by default.** Passing tests do not replace review;
  explicit user direction can change or end the review workflow.
- **Rebuild before testing built artifacts.** CLI/dist tests against a stale build silently test old code.
- **Report honestly.** The per-TPP summary to the user starts with what needs
  the user — open questions and anything you diverged on — then lists what
  shipped and the findings accepted/vetoed (with one-line reasons).

## Adapting for your project

- **Name the ground truth explicitly** — e.g. "CPython 3.12 via `uv run python -c ...` in the reference submodule", "the staging API", "the RFC's test vectors". The vetting step is only as strong as this.
- **Reviewer choices and review focus** live in the gate — adapt [../second-opinion/SKILL.md](../second-opinion/SKILL.md), and this loop inherits it.
- **Tune the model heuristic** to your roster — the invariant is "risk decides the model", not the specific names.
- **Rename the file conventions** (`_todo/`, `_feat-<name>/`, `_done/`, and the roadmap or queue README) to whatever your plan system uses; the loop doesn't care about paths.
