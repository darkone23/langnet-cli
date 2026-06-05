# Public Static Presence And Crawler-Safe App Boundary

**Status:** active implementation plan

**Feature area:** infra

**Primary handoffs:** @architect, @coder, @scribe, @auditor

## Goal

Make LangNet useful and understandable to public visitors and compliant crawlers
without exposing the interactive lookup workspace as an unbounded crawl surface.

The product boundary is:

- `/`, `/about`, `/evidence`, `/learn`, and language overview pages are public,
  static-ish, cheap, and crawlable.
- `/q`, `/reader`, and `/api/*` are interactive application surfaces and are
  disallowed to bots.
- Legacy root lookup URLs such as `/?lang=...&q=...` are supported for humans
  by redirecting to `/q?...`, while verified crawlers receive `403`.

## Current State

- `/` is a static landing page.
- `/evidence` is a static evidence-policy page.
- `/q` is the canonical lookup workspace.
- `/reader` remains an interactive reader workspace.
- `/api/health` is the process health endpoint.
- `robots.txt` disallows `/api/`, `/q`, and `/reader`.
- The server route policy blocks verified Googlebot from `/api/*`, `/q`,
  `/reader`, and legacy query-bearing root lookup URLs.

## Implementation Targets

### Public Content

Add and maintain lightweight public routes:

- `/about`: mission, evidence policy, intended audience, and project boundary.
- `/evidence`: dictionary witnesses, morphology, generated prose boundaries,
  and caveats.
- `/languages/latin`: Latin-specific public overview.
- `/languages/greek`: Greek-specific public overview.
- `/languages/sanskrit`: Sanskrit-specific public overview.

Each page should:

- link to `/q` for interactive lookup;
- link to `/learn` for pedagogy;
- avoid expensive automatic API calls;
- include useful title and description metadata;
- use existing visual language from the current public landing page.
- use the wording from `docs/GOALS.md`, `docs/VISION.md`, and
  `docs/PEDAGOGICAL_PHILOSOPHY.md`: evidence first, useful first/auditable
  second, tradition with function, and deterministic word-level evidence before
  broader interpretation.

Initial public routes now exist for `/about`, `/evidence`, `/languages/latin`,
`/languages/greek`, and `/languages/sanskrit`. Language pages may call the
lightweight curated `/api/word-of-day` endpoint, but should not trigger live CLI
dictionary work on public page load. The next prose pass should add more
concrete examples and citations only when they can stay static and source-backed.

### App Boundary

Keep these routes interactive and non-crawlable:

- `/q`
- `/reader`
- `/api/*`

Do not reintroduce app-generated `/?lang=...&q=...` links.

### Observability

Continue monitoring:

- `crawler_disallowed_route=true`
- Googlebot API `200`s, which should remain zero
- `status=5xx`
- `rate_limit_would_limit=true`
- `/api/health` as `request_scope=healthcheck`
- `/` as `request_scope=page_view`

## Validation

Use:

```bash
cd webapp && bun run test
cd webapp && bun run check
cd webapp && bun run build
```

For runtime checks after deployment:

```bash
curl -I http://127.0.0.1:43210/
curl -I http://127.0.0.1:43210/about
curl -I http://127.0.0.1:43210/languages/latin
curl -I http://127.0.0.1:43210/q
curl -I http://127.0.0.1:43210/api/health
```

## Non-Goals

- Do not add hard rate-limit enforcement as part of this plan.
- Do not move crawler blocking into Cloudflare.
- Do not make reader/search API content crawlable.
- Do not replace source evidence with generated explanations.
