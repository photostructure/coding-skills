# Technical Project Plan (TPP) Guide

> Bundled reference copy. If the project has its own `docs/TPP-GUIDE.md`, that
> file wins — this one is the generalized template from
> <https://photostructure.com/coding/claude-code-tpp/>.

## What is a TPP?

A TPP is a living handoff document for complex work that may span multiple agent
sessions or multiple engineers.

Each engineer reads it, does work, documents discoveries, and updates the file
so the next engineer can continue without starting over.

Every bit of context in the TPP should help the next engineer succeed.

## Golden rule

A good TPP transfers expertise, not just instructions.

It should explain:

- What problem we are solving for users
- Which approaches were considered
- Which approaches failed, and why
- Which tests and edge cases reveal the problem
- How to adapt if nearby architecture changes

These same answers serve four readers: the next session, the reviewer of the PR, the engineer drafting release notes, and whoever inherits this code years from now. Write once; serve all four.

## Typical process

1. An issue is raised, initial design and research is done, and a TPP is created.
2. Engineer A works on the TPP and updates it with discoveries, challenges, and
   next steps.
3. Engineer B picks up where Engineer A left off, using the TPP to continue the
   work.
4. The cycle continues until the TPP is complete.
5. The completed TPP moves to `_done/`.

Update the TPP as progress is made. The file is the handoff.

## Where TPPs live

Choose one primary backlog layout for this project. A temporary feature
integration queue may overlay either layout.

### Simple layout

- `_todo/`: unfinished TPPs
- `_done/`: completed TPPs

### Priority layout

- `_active/`: actively being worked on or targeting the next release
- `_p1/`: high-impact work that should become active soon
- `_p2/`: planned near-term work
- `_p3/`: worthwhile but not imminent
- `_p4/`: nice-to-have work with no timeline
- `_done/`: completed TPPs

Filenames should be date-prefixed:

```text
YYYYMMDD-feature-name.md
```

If using priority folders, moving a file between folders changes its priority.
The filesystem location is the source of truth.

### Feature integration queues

Use `_feat-<name>/` when several TPPs must be coordinated and merged together
on a feature branch, for example `_feat-auth/` or `_feat-face/`. This is a
temporary integration queue, not another priority level.

Each feature queue must contain a `README.md` defining its purpose, owning
branch or worktree, dependency and merge order, completion gate, and the
priority/frontmatter policy for its TPPs. That README is the feature arc — see
[How long should a TPP be?](#how-long-should-a-tpp-be) — so keep it to the shape
of the work and leave implementation detail to its children. Remove the queue
after its completed plans move to `_done/` and the feature merges.

## Frontmatter

Use YAML frontmatter when scripts, dashboards, issue trackers, or backlog tools
need structured data.

```yaml
---
title: Face detection and clustering
section: AI & Vision
priority: p1
issue: https://github.com/example/project/issues/122
votes: 42
---
```

Adapt the fields to this project. Common fields:

- `title`: human-readable task title
- `section`: product area or subsystem
- `priority`: `p1`, `p2`, `p3`, or `p4` if using priority folders
- `issue`, `forum`, `discord`: links to discussion
- `votes`, `views`: demand signals
- `shelved: true`: evaluated and deferred indefinitely

If using priority folders, `priority` must match the folder. For a TPP in a
`_feat-<name>/` queue, follow the effective priority documented by the
project-specific guide or that queue's `README.md`.

## Placeholder TPPs

Lower-priority work may start as a placeholder TPP: frontmatter plus a short
description. Do not add phases, alternatives, or task breakdowns until the work
is close enough to need real scoping.

```markdown
---
title: "On this day" gallery
section: UX & Viewer
priority: p3
issue: https://github.com/example/project/issues/232
votes: 17
---

# TPP: "On this day" gallery

Show assets from the same calendar date in prior years. Natural companion to tag
galleries; likely needs date-aware aggregation and a viewer entry point.
```

## Full TPP structure

```markdown
---
title: Feature name
section: Product area
priority: p1
---

# TPP: Feature name

## Summary

Short description of the problem, under 10 lines.

## Current phase

Next: the one thing the next session does first.

- [x] Research — finding, or a pointer to where it landed
- [x] Breaking tests — `test/foo.test.ts:"rejects empty tag"`
- [ ] Design settled — Option A, pending B's perf numbers
- [ ] Implementation
- [ ] Integration verified — `npm run test:integration`
- [ ] Reviewed

These are independent state, not a sequence: work loops back. Re-open a box when
new information invalidates it and say why in Lore. Name the boxes this plan
actually has — the list above is an example, not a ritual to reproduce.

## Required reading

YOU MUST study these before continuing. Work may be rejected if you skip them.

- **AGENTS.md**: project structure, local rules, and verification commands
- **CLAUDE.md** (when present): additional compatibility instructions
- **[TPP-GUIDE.md](./TPP-GUIDE.md)**: this workflow
- Add project-specific design, testing, API, and architecture docs here
- Add source files that define the subsystem

## Description

Detailed context about the problem, under 20 lines.

## Lore

- Non-obvious details that will help the next engineer
- Prior gotchas that tripped up previous sessions
- Relevant functions, classes, constraints, and historical context

## Solutions

It is OK to be unsure. Mark uncertainty clearly so the next engineer knows what
to verify.

### Option A (preferred)

Describe the preferred approach. Include pros, cons, code snippets, and why this
approach is preferred when useful.

### Option B (alternative)

Describe any serious alternative and why it was rejected or deferred.

## Tasks

Each task names its deliverable and the **acceptance test that proves it** — the
test file and case, or the exact command to run. A runnable test is a shorter
and stricter spec than a paragraph of implementation notes. Add prose only for
integration points a test can't express.
```

## Keeping TPPs useful

Every line must be something the next session could not cheaply rediscover. Cut
anything the code, the tests, or `git log` already say.

**Prefer a pointer to prose.** Name the test that pins the behavior, the commit
that broke it, the file that defines the constraint — don't describe them. The
next session can read the real thing, and the real thing doesn't go stale.

**Never record a count that drifts.** "36 tests passing", "12 files changed",
coverage percentages — all stale the moment the next commit lands, and worse
than useless: a reviewer who spots the mismatch spends their attention arguing
that the number is off by one instead of on the work. Record the command that
produces the number, not the number. `npm test -- tag-gallery` passes is a
durable claim; "36 tests pass" is a hostage to the next commit.

The high-value sections are **Lore** and the failed approaches under
**Solutions**: gotchas, dead ends, and the *why* behind decisions are exactly
what a fresh session cannot recover from the repository. Everything else is
scaffolding — keep it thin.

These four readers all pay for bloat and all benefit from the same edit: the
next session, the PR reviewer, whoever drafts the release notes, and whoever
inherits this code years from now. Trim process ceremony, not the reasoning.

## How long should a TPP be?

Wrong question — and any number that answers it becomes an anchor people write
toward. **Length is a symptom. The rule underneath it is focus.**

A TPP covers one coherent piece of work. The test: say what it does in one
sentence, without an "and". If you can't, you're holding either a plan that
needs trimming or a feature arc that needs children.

Why it matters isn't tidiness. Every line you leave in costs the next engineer
attention and context window — a budget they cannot top up, spent on your notes
instead of the problem. Writing a tome spends someone else's scarcest resource.

Three rules, no arithmetic:

- **Never pad.** A 60-line plan that says everything beats a 200-line plan
  saying the same thing. The template is a menu, not a form: delete any heading
  with nothing worth saying under it.
- **Never trim reasoning to hit a number.** If a plan is long because it carries
  hard-won lore, it is correctly long. Cut scaffolding, restated code, and
  drifting counts first — and if it's still long after that, it's fine.
- **Treat length as a prompt to re-read, not a limit.** Somewhere past a couple
  hundred lines, stop and ask the focus question. Usually the answer is bloat.
  Occasionally it's an arc.

### When the work really is bigger

Don't shred a focused plan into siblings that must coordinate — that moves the
complexity into the gaps between files, where nobody owns it. Promote it to a
**feature arc** instead: one coordination TPP over several focused children.

The arc owns the shape of the work — dependency and merge order, the completion
gate, the lore every child needs, and the one-sentence purpose. The children own
the work itself: their own tasks, tests, and gotchas. An arc that starts
accumulating implementation detail has stopped being an arc and become a tome
with extra steps.

An arc stays short *because* its children are focused. In the layouts above, the
arc is the `_feat-<name>/README.md`.

Children need real seams: each must be **independently testable and
independently mergeable**. If a child can't be verified without its sibling's
code, that isn't a seam — it's one plan wearing two filenames.

## Handoff rules

When context is running low or the session is ending:

1. Re-read the TPP.
2. Mark completed tasks.
3. Update the current phase.
4. Add discoveries, gotchas, and failed approaches.
5. Clarify exactly what remains.
6. Trim redundancy before saving.

The next session should be able to invoke the `tpp` skill with the plan path, read the
TPP, and continue without asking what happened last time.
