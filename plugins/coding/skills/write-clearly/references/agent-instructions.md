# Agent-instruction clarity

Use this standard for text that a coding agent must execute literally:
instructions, plans, specifications, review findings, acceptance criteria,
status reports, and handoffs.

## Contents

- [Preserve the contract](#preserve-the-contract)
- [Name the concrete elements](#name-the-concrete-elements)
- [Make instructions executable](#make-instructions-executable)
- [Control scope and logic](#control-scope-and-logic)
- [Use modal words consistently](#use-modal-words-consistently)
- [Keep the structure readable](#keep-the-structure-readable)
- [Replace confidence language with proof](#replace-confidence-language-with-proof)
- [Audit the result](#audit-the-result)
- [Examples](#examples)
- [Adapt the standard to software](#adapt-the-standard-to-software)

## Preserve the contract

Before rewriting:

1. Identify the audience, document type, and action the text must enable.
2. Preserve code identifiers, commands, paths, API names, quoted text, normative
   keywords, and established project terminology exactly. Redact secrets and
   identify each redaction.
3. Separate source wording that cannot change from prose that can change.
4. Find missing facts that affect meaning. Ask for them or mark them as
   unresolved; do not invent precision.
5. Do not add safeguards, compatibility guarantees, test cases, platforms,
   retry rules, or acceptance criteria that the source does not require. Present
   a plausible improvement as a proposal or question, not as a rewritten
   requirement.

If missing facts prevent an executable rewrite, say that the instruction is
blocked and ask only the questions that control execution. Do not fill the gaps
with a generic best-practice template, placeholder steps, or angle-bracket
slots.

## Name the concrete elements

- Name the actor, action, object, condition, constraint, and expected result
  whenever each element affects execution.
- Use one term for one concept. Do not rotate synonyms for style.
- Use each term with one established meaning in the current scope. Qualify a
  term when the project uses it for different concepts.
- Repeat a noun when *it*, *they*, *this*, or *that* could refer to more than
  one thing.
- Introduce an abbreviation once. Keep canonical domain terms and exact
  identifiers even when they are long.
- Unpack long prose noun stacks with a preposition or clause. Treat three nouns
  as a review signal, not a limit on canonical terms or identifiers.
- Replace vague words such as *thing*, *stuff*, *handle*, *support*, *check*,
  *ensure*, *improve*, *update*, *fix*, and *clean up* with the named object and
  operation.
- Avoid slang, idioms, and opaque phrasal verbs. Prefer a direct verb whose
  ordinary meaning matches the intended action.

## Make instructions executable

- Write an instruction as an imperative with an explicit object: “Run the
  migration,” not “The migration should be run.”
- Name the actor when ownership or causality matters. Use passive voice when the
  actor is unknown, irrelevant, or less important than the result; do not invent
  an actor to avoid passive voice.
- Put a prerequisite or condition before the action when the reader must know
  it first: “If the cache is empty, fetch the record.”
- Put one independently verifiable action in each step. Combine actions only
  when they must occur together.
- Put the expected result, limit, or acceptance criterion directly after the
  action that it verifies.
- Use numbered lists for required sequence and bullets for unordered sets.
- Make every list item complete relative to its lead-in. Keep list items at the
  same logical level.
- Put required actions in steps, not in notes. Use notes only for explanatory
  information.
- For a material risk, state the triggering condition, preventive action, and
  concrete consequence.

## Control scope and logic

- State scope with named files, components, actors, inputs, versions, and
  environments. Do not write *relevant*, *appropriate*, *as needed*, *where
  possible*, *etc.*, or *and so on* without defining the selection rule.
- Define operational states such as *ready*, *done*, *blocked*, and *safe* with
  an observable condition.
- Replace relative quantities and times such as *large*, *small*, *recent*,
  *soon*, *often*, and *a few* with a threshold, range, date, count, or explicit
  comparison when the value affects the task.
- State whether numeric and time boundaries are inclusive. Prefer an explicit
  operator, minimum, maximum, or deadline to *between*, *within*, *above*,
  *below*, *over*, or *up to*.
- State Boolean scope with terms such as *every*, *at least one*, *exactly one*,
  *one or both*, *neither*, or *zero*. Do not leave *any* or *either* to define
  the logic.
- State whether alternatives are inclusive, exclusive, ordered, or optional.
  Avoid *and/or*.
- Check every use of *with*. Name whether it means possession, accompaniment,
  condition, or instrument.
- Use connectors that state the relationship: *because* for cause, *therefore*
  for result, *but* for contrast, and *then* for sequence.
- State the positive case directly. Avoid stacked negatives and exceptions to
  exceptions.

## Use modal words consistently

| Word | Use only for |
| --- | --- |
| **must** / **must not** | A requirement or prohibition |
| **should** | A recommendation that permits exceptions |
| **may** | Permission |
| **can** | Capability |
| **might** / **could** | A possibility with a named condition or uncertainty |
| **will** | Behavior guaranteed by a contract, logic, or established plan |

Do not use a modal word to soften an instruction. If the source does not
establish the force of *maybe*, *should*, *can*, or *may*, do not retain that
modal in the rewrite. Label the statement as a proposal or ask which force
applies.

## Keep the structure readable

- Give each sentence one primary topic. Aim for at most 20 prose words in an
  action and 25 in an explanation. Treat these limits as review signals, not
  reasons to omit necessary words.
- Ignore code, commands, URLs, paths, identifiers, and quoted strings when
  judging sentence length.
- Give each paragraph one topic. Start with the point, then add evidence or
  explanation.
- Cut words that do not change execution: *please note that*, *it is important
  to*, *be sure to*, *in order to*, restated context the reader already has.
  Spend words on scope, conditions, and evidence, not emphasis.
- Split dense conditions, actions, alternatives, or acceptance criteria into a
  vertical list.
- Keep required conditions, actions, and acceptance criteria out of
  parentheses. Use parentheses for short definitions, identifiers, and
  references.
- Keep observation, inference, requirement, recommendation, and open question
  visibly distinct.

## Replace confidence language with proof

- Replace *properly*, *correctly*, *robust*, *safe*, *simple*, *obvious*,
  *significant*, and similar judgments with observable behavior or a named
  criterion.
- Distinguish what was observed from what was inferred. Mark unknowns and
  assumptions explicitly.
- Give an acceptance criterion for each requested outcome when the surrounding
  workflow needs verification.
- In status and review text, name the command, test, trace, source, or code path
  that supports a claim. Do not write “should work” as a result.
- Replace “check” or “ensure” with the exact verification action and its
  observable result.

## Audit the result

Read the revised text once as a literal executor and once as a skeptical
reviewer. Verify that:

- Each action has one actor and one identifiable object.
- Each pronoun has one possible referent.
- Each condition has a clear scope and consequence.
- Each quantity, comparison, and time reference has a usable boundary.
- Each range states whether its endpoints are included.
- Each choice or quantifier has explicit Boolean scope.
- Each modal word has only its declared force.
- Each sequence can be executed in one order.
- Each success claim has observable evidence.
- No rewrite changed a technical requirement.

If more than one reasonable interpretation remains, show the alternatives and
ask one focused question. Do not conceal ambiguity with fluent wording.

## Examples

Vague:

> Handle errors appropriately.

Specific:

> If `readConfig()` returns `ENOENT`, return the default configuration. Propagate
> every other error unchanged.

Vague:

> Update the relevant tests and make the parser more robust.

Blocked:

> The instruction does not identify the parser behavior, inputs, or test scope.

Ask which inputs the parser must accept or reject, what each rejected input must
return, and which test files or suites are in scope. Do not invent test cases.

Vague:

> This should work now.

Specific:

> `npm test -- parser.spec.ts` passes all 18 tests. The new regression test
> covers the previously failing empty-header input.

## Adapt the standard to software

Do not narrow technical vocabulary in the name of plain language. Preserve:

- Canonical software terms, even when they exceed three words
- Established noun and verb uses such as *build*, *commit*, *diff*, *cache*,
  *mock*, *fork*, and *patch*
- Perfect and progressive tenses when completion or duration carries meaning
- Passive voice when the actor is unknown or irrelevant
- Nested lists when hierarchy is the information
- Literal strings, command output, filenames, API signatures, and quoted user
  text
- The repository's spelling, terminology, formatting, and normative vocabulary
