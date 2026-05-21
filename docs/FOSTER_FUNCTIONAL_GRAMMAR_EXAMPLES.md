# Foster Functional Grammar Examples

Foster labels explain the job a form can do in a sentence. They do not replace
native grammar, source evidence, or ambiguity. A reliable display should show
the observed form, the source-backed grammatical parse, and the Foster label
together.

| Foster label | Native grammar examples | Learner reading |
| --- | --- | --- |
| Naming Function | Greek `λόγος`, Sanskrit `putraḥ`, Latin `puella` as nominative singular | The form can name the subject or main topic. |
| Receiving Function | Greek `λόγον`, Sanskrit `putram`, Latin `puellam` as accusative singular | The form can receive the action. |
| Possessing Function | Greek `λόγου`, Sanskrit `putrāṇām`, Latin `puellae` as genitive | The form can mark possession, association, or belonging. |
| To-For Function | Greek `λόγῳ`, Latin `puellae` as dative | The form can mark a recipient, goal, or beneficiary. |
| By-With-From-In Function | Sanskrit instrumental or ablative forms; Latin ablative forms | The form can mark means, accompaniment, source, or separation. |
| In-Where Function | Sanskrit locative forms; Greek and Latin location uses by context | The form can mark where something happens. |
| Calling Function | Greek `λόγε`; Sanskrit and Latin vocative forms | The form can address someone or something directly. |

## Good Lookup Displays

For `putraa.naam`, a learner should see:

- observed form: `putrāṇām`
- lemma: `putra`
- native grammar: masculine genitive plural
- Foster label: Possessing Function; Group; Male
- evidence source: Heritage morphology
- action: load the `putra` declension table and highlight genitive plural

For `puellae`, a learner should see ambiguity instead of one forced answer:

- `puellae`: feminine genitive singular, Possessing Function; Single; Female
- `puellae`: feminine dative singular, To-For Function; Single; Female
- `puellae`: feminine nominative plural, Naming Function; Group; Female

For `λόγου`, a learner should see:

- observed form: `λόγου`
- lemma: `λόγος`
- native grammar: masculine genitive singular
- Foster label: Possessing Function; Single; Male
- evidence source: Diogenes/Morpheus analysis when present on the Diogenes page
- action: load the Diogenes inflection table and highlight genitive singular

## Source Policy

Foster labels are display metadata derived from source-backed features such as
`has_case`, `has_number`, `has_gender`, `has_person`, `has_tense`, `has_voice`,
and `has_mood`. When those features are missing, LangNet should say that the
candidate is unresolved rather than inventing a paradigm.
