# Orion copy system

Project Orion copy should make the product feel like a source-aware reading
desk, not a generic chatbot or a marketing page. Public copy uses **Project
Orion** or **Orion**. The internal name **LangNet** belongs in developer docs,
CLI/runtime descriptions, schemas, and adapter notes.

## Source of truth

- Shared UI and public-site copy lives in `webapp/src/lib/ui-copy.ts`.
- Public route components should import `uiCopy.publicSite` instead of hard-coding prose.
- Repeated public page structures should use shared components under `webapp/src/lib/public/`.
- English is the only active locale today, but copy should stay in the i18next resource tree so future localization is an extraction problem, not a rewrite.

## Voice

Use the project language from `docs/`:

- Evidence before fluency.
- Useful first, auditable second.
- Never present Orion as an oracle.
- Clarity before completeness.
- Determinism before inference.
- Tradition with function.

## Cast of readers

Write for four recurring readers:

- Students need a first reading path from form to meaning.
- Teachers need concise explanations with defensible source support.
- Researchers need provenance, disagreement, and caveats.
- Developers need stable structured objects and inspectable contracts.

## Public pages

Crawler-safe public pages should explain the project and invite lookup without invoking expensive source work during SSR. Dynamic public cards may call lightweight curated endpoints such as `/api/word-of-day`, but expensive dictionary lookup belongs behind `/q` and the attested API request flow.

## Avoid

- Do not promise final interpretation of a passage.
- Do not collapse source disagreement into a single confident answer.
- Do not describe generated text as source evidence.
- Do not add route-local prose when it belongs in `uiCopy.publicSite`.
