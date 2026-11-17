# How to commit

Use these rules in staging, commit planning, and review workflows. User
instructions take precedence over workflow defaults; preserve the repository's
Git history safeguards and unrelated work.

A direct instruction such as "commit", "approved, commit", or "commit these
changes" authorizes the understood scope. Use the supplied message or compose
one; its exact wording needs no separate approval. Honor approved scope and
grouping. Ask only when the scope cannot be determined from the conversation
and repository state.

Skipping review does not authorize a commit. Apply the user's timing and review
instructions in this order:

- **"Commit now" or an explicit instruction to skip review:** stop running
  reviewers without starting or resuming review, even when project instructions
  normally require it. Commit only if the user also authorized committing the
  understood scope; "commit now" supplies that authorization.
- **"Commit when ready" or "review, then commit":** finish the requested,
  running, or project-required review, then commit without another approval
  request. Open questions mean review is unfinished: report them and wait for
  direction.
- **Another direct commit instruction:** finish review of the current changes
  if project instructions require review before every commit. Otherwise,
  verify the staged scope and commit without starting or resuming review,
  requiring a verdict, or asking for approval again.
- **No commit authorization:** follow the active workflow and present the
  proposal before committing.

Use [stage](../skills/stage/SKILL.md) to verify and commit the authorized scope.
A reviewer recommendation does not overrule a user's instruction to commit now.
Accept the user's statement that review already happened and attribute that
statement to them. Do not demand a transcript or `LAND`, invent a review
result, or reopen settled review decisions. Report completed, skipped, and
unfinished review work accurately.
