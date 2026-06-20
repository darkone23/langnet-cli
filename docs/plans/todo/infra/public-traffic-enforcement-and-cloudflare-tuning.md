# Public Traffic Enforcement And Cloudflare Tuning

Status: todo
Owner: @architect, @auditor, @coder
Created: 2026-06-20
Supersedes follow-up enforcement work from:
`docs/plans/completed/infra/anonymous-client-attestation-and-rate-limiting.md`

## Goal

Move LangNet public traffic controls from observe-mode classification to tuned,
deployment-aware soft or enforced limits only after real traffic data has been
reviewed.

## Current Baseline

The webapp already has:

- Cloudflare-aware request identity extraction.
- Anonymous `ln_anon` sessions.
- Client attestation token issuance and verification.
- Client classification.
- Request-cost scoring and response headers.
- Observe-mode rate-limit decisions.
- Rate-limit rollup storage.
- HTTP logs with request identity, attestation, cost, and rate-limit metadata.
- Client-side attestation for same-origin API calls.
- Crawler route policy for disallowed API access.

## Remaining Work

- Review 24 to 48 hours of observe-mode traffic before changing enforcement.
- Decide whether route-scope attestation is sufficient or whether exact
  method/path/query-bound tokens are needed for selected expensive APIs.
- Add `soft` mode only if observe data shows safe thresholds.
- Add route-level 429 blocking first to `/api/search` and `/api/word-index`.
- Tune thresholds for classroom/shared-network use.
- Configure Cloudflare challenge/rate-limit rules for scanner paths and
  expensive API routes.
- Decide whether response cost headers should remain public or become
  log-only.
- Keep process-compose/logrotate settings aligned with the extra request
  metadata volume.

## Acceptance

- Enforcement mode and thresholds are documented before deployment.
- Soft/enforced limits include tests for `Retry-After` and JSON/MessagePack
  compatible 429 responses.
- Cloudflare rules preserve anonymous shareable lookup URLs.
- Traffic rollups demonstrate that legitimate browsing and classroom usage are
  not blocked by default thresholds.
