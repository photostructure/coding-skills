# Reviewer CLI protocol

Use this reference for launches, result validation, environment fallbacks, and
resuming reviewers. The [second-opinion workflow](../SKILL.md) owns scope,
adjudication, stop conditions, and reporting. `<this-skill>` means the parent
`second-opinion` directory, not this `references` directory.

## Launch both reviewers

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
[`../../review/references/single-pass.md`](../../review/references/single-pass.md)
pasted into the prompt instead of naming the skill.

Resolve `<this-skill>` to this skill's directory. Run both commands in the
background and poll each job until it exits:

- **0** — read the review and record the CLI, repository, review scope, session ID,
  pass count, and finding IDs in your task notes. Keep that handle through fixes
  and handoffs (the gate's step 6 defines the handoff record); never select a
  reviewer with `--last` or `--continue`, which can attach to unrelated work. A
  missing session ID does not invalidate the pass, but it forces the
  fresh-session fallback in [Resume reviewers](#resume-reviewers) below.
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

If either CLI is not installed or not authenticated, say so plainly and run
that reviewer as a task-local subagent of a model you can reach, given the same
prompt and the full text of
[`../../review/references/single-pass.md`](../../review/references/single-pass.md).
Save its handle and send the follow-up prompts to that same subagent. Its
findings count, but its verdict is not that model's verdict: the gate's step 6
report marks that model's slot as missing.

## Resume reviewers

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
