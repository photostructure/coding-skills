# Technical Project Plan (TPP) Guide

> Bundled reference copy. If the project has its own `docs/TPP-GUIDE.md`, that
> file wins — this one is the generalized template from
> <https://photostructure.com/coding/claude-code-tpp/>.

## What is a TPP?

A TPP is a living handoff document for complex work that may span multiple agent
sessions or multiple engineers.

Each engineer reads it, does work, documents discoveries, and updates the file
so the next engineer can continue without starting over.

Record context the next engineer needs:

- What problem we are solving for users
- Which approaches were considered
- Which approaches failed, and why
- Which tests and edge cases reveal the problem
- How to adapt if nearby architecture changes

These answers also help PR reviewers, release-note authors, and future
maintainers.

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
- Gotchas in the code or tools that would trip up the next engineer
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

## Working log

Delete this section when the plan is complete. One entry per session, newest
last.

- 2026-11-06, `<cli> 0f3a9c2e-…`, checkout `~/src/worktrees/tag-gallery`.
  Misstep: assumed `tagIds` was sorted; it is insertion-ordered, caught by
  `npm test -- tag-gallery`. Reviewed `src/tags.ts`, 2 passes,
  reviewers `<cli-a> 019a…` and `<cli-b> 5c1d…`: R123-A accepted (empty tag
  list threw), R456-B vetoed (`dedupe` already runs upstream,
  `src/tags.ts:40`).
```

## Keeping TPPs useful

Every line must be something the next session could not cheaply rediscover. Cut
anything the code, the tests, or `git log` already say.

**Prefer a pointer to prose.** Name the test that pins the behavior, the commit
that broke it, the file that defines the constraint — don't describe them. The
next session can read the real thing, and the real thing doesn't go stale.

**Record commands instead of counts that drift.** Test counts, changed-file
counts, and coverage percentages become stale as work continues. Record the
command and its result, such as `npm test -- tag-gallery` passes.

**Keep session records in the Working log, and only until the plan is done.**
While the plan is unfinished, its **Working log** lets the next session see
what earlier sessions tried, so it does not repeat their missteps. Each session
that works the plan appends one entry, at handoff if not sooner, with:

- its CLI and session ID, so the next session can open that transcript;
- its missteps: what looked right, why it was wrong, and how it was caught;
- the checkout that holds uncommitted changes, if any, which the newest entry
  that names one supersedes;
- for each review it ran: the reviewed scope and pass count, each reviewer's CLI and
  session ID, and each finding by ID with its accept, veto, or open state and
  one line of evidence.

Keep session records out of the plan's other sections, and keep paths in a
temporary or scratch directory out of the plan entirely, because they get
deleted.

The finished plan records outcomes: what is true, what was decided and why,
what failed and why. The session that completes the plan moves what lasts out
of the Working log, then deletes the log in the commit that marks the plan done
or moves it to `_done/`. Record each where it lasts:

- The reason for a change goes in its commit message.
- A check that someone must rerun becomes a committed test or script, which
  the TPP names with the command that runs it. A check that cannot be automated
  stays in the TPP as manual steps.
- Review verdicts go in the report to the user. The TPP's **Reviewed** box gets
  the final verdict, each model whose slot is missing and why (as
  `second-opinion` reports it), and the base commit the reviewed diff applies
  to. Each vetoed finding gets one line under **Lore**: the claim, and the
  evidence that refutes it.
- A misstep a later engineer could repeat gets one line under **Lore**.

Keep **Lore** and the failed approaches under **Solutions** focused on context
a fresh session cannot recover from the repository. Cut repeated process
instructions while preserving the reasons for decisions.

## How long should a TPP be?

A TPP covers one coherent piece of work. State its purpose in one sentence
without an "and". If that fails, trim the plan or organize it as a feature arc.
Use focus, not a line budget, to decide its length:

- **Never pad.** Use only the template sections the work needs; delete empty
  headings.
- **Never trim reasoning to hit a number.** If a plan is long because it carries
  hard-won lore, it is correctly long. Cut scaffolding, restated code, and
  drifting counts first — and if it's still long after that, it's fine.
- **Use length as a prompt to re-read.** Past a couple hundred lines, revisit
  the focus question rather than enforcing a limit.

### When the work really is bigger

Keep tightly coupled work in one plan. For work with independently testable
parts, use a **feature arc**: one coordination TPP over focused child plans.

The arc owns the shape of the work — dependency and merge order, the completion
gate, the lore every child needs, and the one-sentence purpose. Children own
their tasks, tests, and gotchas. Keep implementation detail in the children.

An arc stays short *because* its children are focused. In the layouts above, the
arc is the `_feat-<name>/README.md`.

Children need real seams: each must be **independently testable and
independently mergeable**. If a child can't be verified without its sibling's
code, keep that work in one plan.

## Handoff rules

When context is running low or the session is ending:

1. Re-read the TPP.
2. Mark completed tasks.
3. Update the current phase.
4. Add discoveries, gotchas, and failed approaches.
5. Append this session's **Working log** entry, including its missteps and any
   review still in progress.
6. Clarify exactly what remains.
7. Trim redundancy before saving.

The next session should be able to invoke the `tpp` skill with the plan path, read the
TPP, and continue without asking what happened last time.
