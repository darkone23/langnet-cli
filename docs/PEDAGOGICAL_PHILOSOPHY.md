# Pedagogical Philosophy

LangNet should teach by making evidence intelligible. Its job is not only to return data; it should help readers understand how a form, meaning, and source fit together.

## Learning Model

Classical-language reading usually involves three linked questions:

1. What form am I looking at?
2. What meanings can this lexeme carry?
3. Which meaning is plausible here?

LangNet currently focuses on the first two questions at word level. The third question depends on passage context and should wait until word-level claims and sense buckets are stable.

## Display Priorities

Learner-facing output should appear in this order:

1. Headword or observed form.
2. Grouped meanings.
3. Morphology.
4. Citations and source evidence.
5. Source disagreements or caveats.

Backend names, raw payloads, and internal IDs should remain inspectable, but they should not be the first thing a student has to understand.

## Grammar Policy

Use traditional terminology, but pair labels with function when that helps comprehension.

The project calls this Foster functional grammar: a display vocabulary that describes the job a form is doing while preserving the conventional grammatical label. In current design terms, Foster labels are learner-facing explanations, not replacements for precise morphology.

| Label | Learner-facing function |
| --- | --- |
| nominative | naming or subject function |
| accusative | receiving or object function |
| genitive | belonging, source, or description function |
| dative | to/for function |
| ablative | from/by/with function |
| instrumental | by/with function |
| locative | place/time where function |
| vocative | direct address |

Internal data should stay technically precise. Display copy can add functional explanation without weakening the grammatical label.

## Foster Display Vocabulary

The stable learner-facing vocabulary should stay small and cross-language:

| Foster label | Typical grammatical scope |
| --- | --- |
| Naming Function | nominative, subject, main topic |
| Calling Function | vocative or direct address |
| Receiving Function | accusative or direct object |
| Possessing Function | genitive, belonging, source, relationship |
| To-For Function | dative, recipient, beneficiary, purpose |
| By-With-From-In Function | ablative, instrumental, separation, means, accompaniment |
| In-Where Function | locative, place, time where |
| Time-Now / Time-Later / Time-Past | tense display where useful |

These labels should be optional display aids. JSON claims should continue to carry exact predicates such as `has_case`, `has_tense`, `has_voice`, and `has_mood`.

## Evidence Policy

Students should be able to trust the explanation without treating LangNet as an oracle. When sources disagree, are incomplete, or expose raw encodings, the output should say so plainly.

This matters especially for Sanskrit dictionary glosses and bilingual sources. Translated glosses should not influence semantic grouping until they are cache-backed and represented as translation evidence.

## Non-Goals For Now

- Passage-level interpretation before word-level evidence is reliable.
- Opaque generated answers that cannot point back to sources.
- Replacing source dictionaries or grammars.
- Hiding uncertainty in order to make output look smoother.
