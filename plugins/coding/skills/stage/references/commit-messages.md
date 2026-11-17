# Commit messages

Draft a [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) message from the staged diff.

## Format

```
<type>[(<scope>)][!]: <description>

[problem and rationale; omit only if clear from subject]

[optional footer(s)]
```

## Spec summary

- **Type** (REQUIRED): a noun prefix. `feat` = new feature, `fix` = bug fix. Other common types: `refactor`, `perf`, `test`, `docs`, `style`, `build`, `ci`, `chore`.
- **Scope** (optional): a noun in parentheses after the type describing the section of the codebase, e.g. `fix(parser):`. Use the most significantly changed filename (no extension/path).
- **`!`** (optional): append immediately before `:` to flag a breaking change, e.g. `feat!:` or `feat(api)!:`.
- **Description** (REQUIRED): a concrete, imperative subject. Avoid task-status summaries such as "finish cleanup".
- **Body**: for nontrivial changes, explain the problem and why this fix in a short paragraph. Omit only when the subject conveys the rationale.
- **Footer(s)** (optional): one blank line after body. Format: `token: value` or `token #value`. A `BREAKING CHANGE:` footer (uppercase) is synonymous with `!` in the type prefix.

## Trailers (attribution + references)

Add git trailers whenever the conversation provides the data, so credit and links aren't lost:

- `Reported-by: <name>` — a third party reported it: a user, customer, forum poster, or issue filer
- `Link: <url>` — a thread, issue, or message that gives context (no auto-close)
- `Refs: <#NNN | url>` — related issue you do **not** want to auto-close
- `Closes: #NNN` / `Fixes: #NNN` — a GitHub issue to auto-close on merge
- `Fixes: <12-char-sha> ("subject")` — the bug-introducing commit (Linux-kernel form)

`Reported-by` credits someone **outside** the work. Never name the repo owner, the person you are working with, or yourself — a maintainer finding a bug in their own project is not a bug report, and the commit's authorship already records who wrote the fix. When nobody outside reported it, omit the trailer.

Repeat a trailer for multiple values (one per line) — never `Reported-by: a, b`. Prefer `git commit --trailer "Reported-by=name" --trailer "Link=https://..."` (git ≥2.32) so formatting stays canonical.

## Constraints

- Keep the message under 10 lines (subject + blank + body + footers) unless the
  user supplies or approves a longer message.
- If a draft needs more space, shorten it or propose splitting by topic before
  approval. Do not reopen approved scope or grouping to meet the line limit.
- Match the recent commits read in stage's **Gather live context** step. Check that the complete proposal explains why.

**NEVER include**: Co-Authored-By trailers, AI attribution, line-by-line enumeration.
