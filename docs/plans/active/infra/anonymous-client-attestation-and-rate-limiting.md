# Anonymous Client Attestation And Rate Limiting

**Status:** active design plan

**Feature area:** infra

**Primary handoffs:** @architect, @coder, @auditor

## Goal

Protect LangNet's public web and API surfaces from automated scraping pressure
without requiring user accounts or breaking anonymous, shareable lookup URLs.

The target is cooperative client attestation, not strong browser
authentication. A well-behaved web UI client should be able to say: "I came
through the expected LangNet web flow recently." Non-attesting clients can
remain functional, but should receive stricter limits and lower trust.

## Current Observations

Recent `process-compose` logs show traffic patterns that look mostly scripted:

- legacy shareable page loads such as
  `/?lang=grc&q=...&translation=auto&theme=manuscript&dictionary=diogenes`;
  current app-generated lookup URLs use `/q?...` instead;
- follow-on `/api/search` calls with fixed dictionaries such as `diogenes`,
  `bailly`, `gaffiot`, `cdsl`, `whitakers`, and `strongs_greek`;
- follow-on `/api/word-index?mode=nearby...` calls;
- query sequences that look like lexicon/headword walks rather than reading
  sessions;
- commodity probes such as `/wp-admin/install.php`;
- regular `Go-http-client/1.1` Caddy aborts against `/`, likely health-check or
  monitor noise rather than the main scraper signal.

The app currently sees local proxy addresses in logs. Because the deployment is
behind Cloudflare, request identity should be derived from Cloudflare-aware
headers such as `CF-Connecting-IP`, `CF-Ray`, and `CF-IPCountry`, with careful
fallbacks.

## Research Summary

Sources checked:

- Cloudflare HTTP headers:
  <https://developers.cloudflare.com/fundamentals/reference/http-headers/>
- Cloudflare rate limiting rules:
  <https://developers.cloudflare.com/waf/rate-limiting-rules/>
- Cloudflare rate limiting best practices:
  <https://developers.cloudflare.com/waf/rate-limiting-rules/best-practices/>
- SvelteKit hooks:
  <https://svelte.dev/docs/kit/hooks>
- SvelteKit cookies and request event APIs:
  <https://svelte.dev/docs/kit/@sveltejs-kit>
- AWS Signature Version 4 query signing:
  <https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-query-string-auth.html>
- Google Cloud canonical requests:
  <https://docs.cloud.google.com/storage/docs/authentication/canonical-requests>

Key conclusions:

- Cloudflare explicitly supports content-scraping rate-limit patterns based on
  paths, query strings, cookies, headers, and other request characteristics,
  depending on plan capabilities.
- Cloudflare documentation recommends cookie-based counting characteristics for
  session-aware limiting where IP-only limits are too blunt.
- SvelteKit `handle`, `event.cookies`, and `event.locals` are the correct
  integration points for anonymous sessions, request classification, and
  per-route metadata.
- Canonical request signing patterns should bind signatures to method, path,
  sorted query parameters, timestamp, expiry, and session identity.
- Browser-side signing should be treated as attestation, not authentication,
  because browser code cannot keep secrets from determined clients.

## Architecture

Use three layers:

1. Cloudflare edge controls.
2. SvelteKit anonymous session and request classification.
3. Route-level semantic rate limits informed by LangNet-specific request cost.

### Cloudflare Layer

Cloudflare should handle coarse abuse before traffic reaches SvelteKit:

- block or challenge scanner paths such as `/wp-admin/*`, `/xmlrpc.php`, and
  common exploit probes;
- rate-limit route-driven lookup traffic matching `path="/"` with query
  parameters like `q` and `dictionary`;
- rate-limit expensive API paths such as `/api/search*` and
  `/api/word-index*`;
- use bot score, JA3/JA4, ASN, country, cookie, query, or header counting
  characteristics where available;
- preserve `CF-Connecting-IP`, `CF-Ray`, and related request headers to the
  origin.

Cloudflare should not be the only enforcement layer because the application has
domain-specific cost information that Cloudflare cannot infer by default.

### SvelteKit Layer

SvelteKit should issue and use an anonymous session cookie:

```http
Set-Cookie: ln_anon=<opaque-session-id>; HttpOnly; SameSite=Lax; Path=/
```

Use `Secure` in production. Suggested session TTL: 12 to 24 hours.

Each request should be classified into one of:

- `trusted_web_session`: valid anonymous session and valid client attestation;
- `anonymous_unattested`: missing or invalid attestation, but not clearly
  abusive;
- `suspicious`: scanner path, repeated invalid attestations, extreme rate
  behavior, or known hostile pattern.

Classification metadata should be stored in `event.locals` for API handlers and
logging.

### Client Attestation Layer

The web UI should request a short-lived token from the server before expensive
API calls and attach it as a header:

```http
X-LangNet-Client-Attestation: <payload>.<hmac-signature>
```

The token means:

> This request came through the LangNet web interaction flow recently for this
> anonymous session.

It does not mean:

> This is a human, this is unscriptable, or this client is authenticated.

Suggested token payload:

```json
{
  "sid": "anonymous-session-id",
  "iat": 1780589000,
  "exp": 1780589300,
  "nonce": "random",
  "scope": "api:expensive",
  "method": "GET",
  "path": "/api/search",
  "query_hash": "sha256(canonical-query)",
  "client": "web-ui"
}
```

Signing should use HMAC-SHA256 with an origin-only secret such as
`LANGNET_CLIENT_ATTESTATION_SECRET`.

Canonicalization should sort query parameters and bind the token to the exact
method, path, query hash, anonymous session id, and expiry.

Missing or invalid attestation should initially downgrade the client class, not
break anonymous access.

### Semantic Rate Limiting Layer

LangNet should apply app-side limits using request semantics:

- route path;
- anonymous session id;
- Cloudflare client IP;
- dictionary/provider;
- language;
- query shape;
- translation mode;
- client class;
- estimated request cost.

Initial route focus:

- `/api/search`;
- `/api/word-index`, except cheap `mode=sections`;
- `/api/paradigm`;
- `/api/encounter-briefing`;
- translation-cache maintenance operations.

Suggested initial limits:

| Client class | Route | Limit |
| --- | --- | --- |
| `trusted_web_session` | `/api/search` | 20/minute, 200/hour |
| `anonymous_unattested` | `/api/search` | 5/minute, 40/hour |
| `suspicious` | `/api/search` | 1/minute |
| `trusted_web_session` | `/api/word-index` | 30/minute, 300/hour |
| `anonymous_unattested` | `/api/word-index` | 10/minute, 80/hour |
| `suspicious` | `/api/word-index` | 2/minute |

Dictionary-specific limits should be added for expensive providers such as
`diogenes`, `bailly`, `gaffiot`, and `cdsl`.

Rate-limit responses should use:

```http
429 Too Many Requests
Retry-After: <seconds>
```

Response payloads should remain JSON/MessagePack compatible with the existing
web client.

### Request Cost Scoring

Add a request cost score so the app can observe expensive traffic and later
integrate with Cloudflare complexity-aware or response-header-based rate
limiting if available.

Suggested response headers:

```http
LangNet-Client-Class: trusted_web_session
LangNet-Attestation: valid
LangNet-Request-Cost: 25
```

Example cost model:

- cheap static sections: `1`;
- `/api/word-index?mode=nearby`: `5`;
- `/api/search?translation=cache`: `10`;
- `/api/search?translation=auto`: `25`;
- Diogenes/Bailly/Gaffiot long-running request: add extra cost;
- timeout or backend error: add extra cost for abuse analysis.

## Implementation Phases

### Phase 1: Observe And Classify

Do this first, without blocking.

- Add Cloudflare-aware request identity extraction.
- Add richer HTTP logs with client IP, `CF-Ray`, country, user-agent, referer,
  route, dictionary, language, translation mode, and query presence.
- Issue `ln_anon` anonymous session cookie.
- Add `event.locals` classification fields.
- Add request cost scoring and response headers.
- Add `LANGNET_RATE_LIMIT_MODE=observe`.
- Add log rotation for the process-compose managed logs so increased
  observability does not produce unbounded log growth.

Validation:

```bash
cd webapp
bun test
bun run check
bun run build
```

### Phase 2: Client Attestation

- Add server-side HMAC signing and verification helpers.
- Add `/api/auth/request-token`.
- Update the `fetchPayload()` wrapper to request and attach attestation headers
  for same-origin `/api/*` calls.
- If token acquisition fails, continue unattested.
- If token is expired, retry token refresh once.
- Keep enforcement in observe mode.

Validation:

```bash
cd webapp
bun src/lib/server/client-attestation.test.ts
bun src/lib/msgpack.test.ts
bun test
bun run check
bun run build
```

### Phase 3: App-Side Rate Limiting

- Add an in-memory limiter keyed by session, client IP, route, dictionary,
  language, translation mode, and client class.
- Start in `observe`.
- Move to `soft` mode where only extreme or suspicious patterns are blocked.
- Move to `enforce` after thresholds are tuned.

Suggested modes:

- `observe`: classify and log, never block;
- `soft`: block extreme/suspicious traffic, report would-block for normal
  buckets;
- `enforce`: apply configured limits.

Validation:

```bash
cd webapp
bun src/lib/server/rate-limit.test.ts
bun test
bun run check
bun run build
```

### Phase 4: Cloudflare Rules

Configure Cloudflare after Phase 1 provides better data.

Candidate rules:

- challenge/block `/wp-admin/*`, `/xmlrpc.php`, and scanner probes;
- rate-limit `/api/search*`;
- rate-limit `/api/word-index*`;
- rate-limit `/?*q=*&dictionary=*`;
- if supported, count by `ln_anon`, `dictionary`, `q`, bot score, ASN, or
  JA3/JA4 fingerprint;
- consider `cf_clearance` reuse limits if Managed Challenge is used.

Cloudflare limits should be tuned to avoid blocking legitimate classroom or
library users behind shared networks.

## Proposed Files

Likely new files:

- `webapp/src/lib/server/request-identity.ts`
- `webapp/src/lib/server/anonymous-session.ts`
- `webapp/src/lib/server/client-attestation.ts`
- `webapp/src/lib/server/client-classification.ts`
- `webapp/src/lib/server/request-cost.ts`
- `webapp/src/lib/server/rate-limit.ts`
- `webapp/src/routes/api/auth/request-token/+server.ts`
- `webapp/src/app.d.ts` updates, if `App.Locals` does not already contain
  suitable fields

Likely modified files:

- `webapp/src/hooks.server.ts`
- `webapp/src/lib/msgpack.ts`
- `webapp/src/lib/server/http-log.ts`
- `webapp/src/routes/api/search/+server.ts`
- `webapp/src/routes/api/word-index/+server.ts`
- `webapp/src/routes/api/paradigm/+server.ts`
- `webapp/src/routes/api/encounter-briefing/+server.ts`
- `webapp/src/routes/api/translation-cache/+server.ts`
- parent-directory process-compose template/config files that generate
  `../process-compose.log`

## Open Questions

- Which Cloudflare plan features are available: Advanced Rate Limiting, Bot
  Management, JA3/JA4, cookie/query counting characteristics?
- Should `ln_anon` be used as a Cloudflare counting characteristic directly?
- What limits are acceptable for classroom/shared-network usage?
- Should route-driven page loads with `q` and `dictionary` be limited at the
  edge, in the app, or both?
- Should `translation=auto` get a separate lower budget from
  `translation=cache`?
- Should response cost headers be exposed publicly or only in observe logs?

## Execution-Grade Implementation Notes

This section is intended for a smaller or faster implementation model. Treat it
as the mechanical plan. Do not infer enforcement behavior beyond what is
written here.

### Required Environment Variables

Use these names exactly:

```text
LANGNET_CLIENT_ATTESTATION_SECRET=<random 32+ byte secret>
LANGNET_RATE_LIMIT_MODE=observe
LANGNET_ANON_SESSION_COOKIE=ln_anon
```

Defaults:

- `LANGNET_RATE_LIMIT_MODE`: `observe`
- `LANGNET_ANON_SESSION_COOKIE`: `ln_anon`
- If `LANGNET_CLIENT_ATTESTATION_SECRET` is absent, token signing should still
  work in development with an explicit deterministic development secret and a
  warning in logs. Production should document that a real secret is required.

Valid rate-limit modes:

```ts
export type RateLimitMode = 'observe' | 'soft' | 'enforce';
```

### Exact App Locals Shape

Add or update `webapp/src/app.d.ts`:

```ts
declare global {
	namespace App {
		interface Locals {
			anonymousSessionId?: string;
			requestIdentity?: import('$lib/server/request-identity').RequestIdentity;
			clientAttestation?: import('$lib/server/client-attestation').AttestationResult;
			clientClassification?: import('$lib/server/client-classification').ClientClassification;
			requestCost?: import('$lib/server/request-cost').RequestCost;
		}
	}
}

export {};
```

If `app.d.ts` already exists with `App.Locals`, merge these fields rather than
replacing unrelated declarations.

### Module Contracts

#### `webapp/src/lib/server/request-identity.ts`

Export:

```ts
export type RequestIdentity = {
	clientIp: string;
	clientIpSource: 'cf-connecting-ip' | 'x-forwarded-for' | 'event-client-address' | 'unknown';
	cfConnectingIp?: string;
	cfRay?: string;
	cfCountry?: string;
	userAgent: string;
	referer: string;
};

export function requestIdentityFromHeaders(
	headers: Headers,
	clientAddress?: string
): RequestIdentity;
```

Rules:

- Prefer `CF-Connecting-IP`.
- Else use first value from `X-Forwarded-For`.
- Else use SvelteKit `event.getClientAddress()` if available.
- Else use `unknown`.
- Preserve `CF-Ray`, `CF-IPCountry`, `User-Agent`, and `Referer`.

Tests:

- `CF-Connecting-IP` wins over `X-Forwarded-For`.
- `X-Forwarded-For` first IP is used when Cloudflare header is missing.
- Missing headers return `unknown` and empty strings for textual metadata.

#### `webapp/src/lib/server/anonymous-session.ts`

Export:

```ts
export const defaultAnonymousSessionCookieName = 'ln_anon';

export type AnonymousSession = {
	id: string;
	isNew: boolean;
	cookieName: string;
};

export function validAnonymousSessionId(value: string | undefined): value is string;
export function createAnonymousSessionId(): string;
export function getOrCreateAnonymousSession(
	cookies: import('@sveltejs/kit').Cookies,
	options?: { secure?: boolean; maxAgeSeconds?: number; cookieName?: string }
): AnonymousSession;
```

Rules:

- Session IDs should be opaque random base64url/hex strings with at least 128
  bits of entropy.
- Accept only simple URL-safe IDs.
- Set cookie with `httpOnly: true`, `sameSite: 'lax'`, `path: '/'`, configured
  max age, and `secure` based on production/runtime option.
- Default max age: 24 hours.

Tests:

- Reuses valid existing cookie.
- Replaces invalid cookie.
- Creates new cookie when absent.

#### `webapp/src/lib/server/client-attestation.ts`

Export:

```ts
export type AttestationPayload = {
	sid: string;
	iat: number;
	exp: number;
	nonce: string;
	scope: 'api:expensive';
	method: string;
	path: string;
	query_hash: string;
	client: 'web-ui';
};

export type AttestationStatus =
	| 'valid'
	| 'missing'
	| 'expired'
	| 'bad_signature'
	| 'query_mismatch'
	| 'session_mismatch'
	| 'method_mismatch'
	| 'path_mismatch'
	| 'malformed';

export type AttestationResult = {
	status: AttestationStatus;
	payload?: AttestationPayload;
};

export function canonicalQuery(searchParams: URLSearchParams): string;
export function queryHash(canonicalQuery: string): string;
export function signAttestation(
	payload: AttestationPayload,
	secret: string
): string;
export function createAttestationToken(input: {
	sessionId: string;
	method: string;
	path: string;
	searchParams: URLSearchParams;
	secret: string;
	nowSeconds?: number;
	ttlSeconds?: number;
}): string;
export function verifyAttestationToken(input: {
	token: string | null;
	sessionId?: string;
	method: string;
	path: string;
	searchParams: URLSearchParams;
	secret: string;
	nowSeconds?: number;
}): AttestationResult;
```

Rules:

- Sort query parameters by key and value.
- Preserve repeated query parameters deterministically.
- Token format: `<base64url-json-payload>.<base64url-hmac>`.
- HMAC algorithm: SHA-256.
- Default TTL: 300 seconds.
- Use constant-time comparison for signatures.
- Do not throw for bad user input; return an `AttestationResult`.

Tests:

- Valid token verifies.
- Expired token returns `expired`.
- Changed query returns `query_mismatch`.
- Changed method returns `method_mismatch`.
- Changed path returns `path_mismatch`.
- Changed session returns `session_mismatch`.
- Tampered signature returns `bad_signature`.
- Reordered query parameters still verify.

#### `webapp/src/lib/server/client-classification.ts`

Export:

```ts
export type ClientClass = 'trusted_web_session' | 'anonymous_unattested' | 'suspicious';

export type ClientClassification = {
	clientClass: ClientClass;
	reason: string;
};

export function classifyClient(input: {
	path: string;
	attestationStatus: import('$lib/server/client-attestation').AttestationStatus;
	anonymousSessionId?: string;
	userAgent: string;
}): ClientClassification;
```

Initial rules:

- Valid attestation with session id: `trusted_web_session`.
- Scanner paths such as `/wp-admin`, `/xmlrpc.php`: `suspicious`.
- Empty or missing session: `anonymous_unattested`.
- Missing/expired/bad attestation: `anonymous_unattested`.
- Do not mark `Go-http-client` suspicious by itself in app code yet; log it.

Tests:

- Valid attestation becomes trusted.
- Missing token becomes anonymous.
- WordPress probe becomes suspicious.

#### `webapp/src/lib/server/request-cost.ts`

Export:

```ts
export type RequestCost = {
	score: number;
	route: string;
	dictionary: string;
	translation: string;
	reason: string;
};

export function requestCostFromUrl(url: URL): RequestCost;
export function appendRequestCostHeaders(headers: Headers, cost: RequestCost): void;
```

Initial scoring:

- default: `1`
- `/api/word-index?mode=sections`: `1`
- `/api/word-index`: `5`
- `/api/search` with `translation=cache`: `10`
- `/api/search` with `translation=auto`: `25`
- `/api/search` with `translation=populate` or `do-it-all`: `40`
- add `10` for dictionaries `diogenes`, `bailly`, `gaffiot`, `cdsl`

Tests:

- Sections cost is cheap.
- Search cache is cheaper than search auto.
- Expensive dictionaries add cost.

#### `webapp/src/lib/server/rate-limit.ts`

Export:

```ts
export type RateLimitDecision = {
	allowed: boolean;
	observedOnly: boolean;
	limit: number;
	remaining: number;
	retryAfterSeconds: number;
	key: string;
	reason: string;
};

export function rateLimitMode(env?: Record<string, string | undefined>): RateLimitMode;
export function checkRateLimit(input: {
	mode: RateLimitMode;
	clientClass: import('$lib/server/client-classification').ClientClass;
	sessionId?: string;
	clientIp: string;
	route: string;
	dictionary: string;
	translation: string;
	nowMs?: number;
}): RateLimitDecision;
```

Rules:

- In `observe`, always return `allowed: true` and `observedOnly: true`.
- In `soft`, block only `suspicious` class over limit.
- In `enforce`, apply all limits.
- In-memory is acceptable for initial single-process deployment.
- Use fixed windows or sliding windows, but tests must control time.

Tests:

- Observe mode never blocks.
- Suspicious class blocks in soft mode after threshold.
- Trusted class has a higher limit than unattested class.
- Retry-after is positive when blocked.

### Hook Integration Details

Modify `webapp/src/hooks.server.ts` in this order:

1. Compute `requestIdentity` from headers.
2. Get or create anonymous session cookie.
3. Compute attestation result for `/api/*` requests using header
   `X-LangNet-Client-Attestation`.
4. Classify client.
5. Compute request cost.
6. Store all values in `event.locals`.
7. Resolve the request.
8. Append response headers:

```http
LangNet-Client-Class: <class>
LangNet-Attestation: <status>
LangNet-Request-Cost: <score>
```

In Phase 1, do not block in `hooks.server.ts`.

### Token Endpoint Details

Create `webapp/src/routes/api/auth/request-token/+server.ts`.

Use `POST`, not `GET`.

Request JSON:

```json
{
  "method": "GET",
  "path": "/api/search",
  "query": "language=grc&q=logos&dictionary=diogenes"
}
```

Response JSON:

```json
{
  "token": "<token>",
  "expires_at": 1780589300
}
```

Rules:

- Require or create `ln_anon` through the hook.
- Only sign same-origin API paths starting with `/api/`.
- Reject paths starting with `/api/auth/` to avoid recursive token requests.
- Return `400` for malformed JSON or invalid path.

### Client Fetch Integration Details

Modify `webapp/src/lib/msgpack.ts`.

Add:

```ts
export const clientAttestationHeader = 'X-LangNet-Client-Attestation';
```

Behavior:

- `fetchPayload()` should call a helper before same-origin `/api/*` requests,
  excluding `/api/auth/request-token`.
- The helper posts to `/api/auth/request-token` with method, path, and query.
- If token fetch succeeds, attach the attestation header.
- If token fetch fails, continue without the header.
- Avoid infinite recursion when token endpoint itself calls `fetchPayload` by
  using raw `fetch` inside the helper.

Tests:

- Same-origin API request receives attestation header when token endpoint
  succeeds.
- Token endpoint request is not recursively attested.
- Failed token endpoint still performs original request without token.

### API Route Limiter Integration

Do not add blocking in Phase 1.

When implementing Phase 3, add a small helper each route can call before doing
CLI work:

```ts
const decision = checkRateLimit({
	mode: rateLimitMode(),
	clientClass: event.locals.clientClassification?.clientClass ?? 'anonymous_unattested',
	sessionId: event.locals.anonymousSessionId,
	clientIp: event.locals.requestIdentity?.clientIp ?? 'unknown',
	route: event.url.pathname,
	dictionary,
	translation,
});

if (!decision.allowed) {
	return respond(
		{ error: 'Too many requests. Please wait and try again.', retry_after: decision.retryAfterSeconds },
		{
			status: 429,
			headers: { 'retry-after': String(decision.retryAfterSeconds) }
		}
	);
}
```

Apply first to:

- `webapp/src/routes/api/search/+server.ts`
- `webapp/src/routes/api/word-index/+server.ts`

Apply later to:

- `webapp/src/routes/api/paradigm/+server.ts`
- `webapp/src/routes/api/encounter-briefing/+server.ts`
- `webapp/src/routes/api/translation-cache/+server.ts`

### Implementation Task Sequence

Use small commits or checkpoints in this order:

1. Add `request-identity.ts` and tests.
2. Update `http-log.ts` and tests to include identity fields.
3. Add `anonymous-session.ts` and tests.
4. Add `App.Locals` fields.
5. Integrate identity/session into `hooks.server.ts`.
6. Add `request-cost.ts` and tests.
7. Add observe-only cost/class headers in `hooks.server.ts`.
8. Add `client-attestation.ts` and tests.
9. Add `client-classification.ts` and tests.
10. Add `/api/auth/request-token`.
11. Add client-side attestation in `msgpack.ts`.
12. Add `rate-limit.ts` and tests in observe mode.
13. Integrate limiter into `/api/search` in observe mode.
14. Integrate limiter into `/api/word-index` in observe mode.
15. Add process-compose log rotation in the parent template/config.
16. Only after observe data review, enable `soft` or `enforce`.

### Process-Compose Log Rotation

The current investigation relied on `../process-compose.log`, and Phase 1 will
increase useful request metadata. Add log rotation at the process manager layer
so logs remain available for analysis without unbounded growth.

Implementation requirements:

- Locate the process-compose template/config in the parent tooling directory
  that controls `../process-compose.log`.
- Prefer native process-compose log rotation settings if available in the
  installed version.
- If native rotation is not available, add a small external rotation strategy
  documented next to the template, rather than ad-hoc truncation.
- Preserve enough history for traffic analysis.

Suggested defaults:

```text
max log file size: 25 MiB
retained files: 5
compression: enabled if supported
```

Validation:

- Regenerate or inspect the rendered process-compose config.
- Confirm the managed web logs still write to the expected path.
- Confirm rotation settings are present in the rendered config or documented
  fallback.
- Do not delete existing logs during implementation.

### Verification Expectations

The implementer should run focused web tests after each task and full web gates
after integration:

```bash
cd webapp
bun test
bun run check
bun run build
```

Run Python stabilization only if Python files or CLI behavior are touched:

```bash
just validate-stabilization
```

Final validation and verification will be reviewed by GPT-5.5. The
implementation agent should preserve clear evidence in final notes:

- commands run;
- pass/fail output summary;
- any mode left as `observe`;
- whether enforcement is enabled;
- whether a production build was run.

### Non-Goals For Initial Implementation

- Do not require login.
- Do not block all unattested clients.
- Do not add CAPTCHA.
- Do not add persistent external stores unless single-process memory is proven
  insufficient.
- Do not implement nonce replay storage in Phase 1.
- Do not assume `Go-http-client` alone is malicious.
- Do not remove shareable lookup URLs.

## Recommendation

Start with observability, not enforcement.

The current traffic looks mostly automated, but LangNet intentionally supports
anonymous educational use. The safest path is:

1. identify real clients behind Cloudflare;
2. issue anonymous sessions;
3. classify and cost requests;
4. observe traffic for 24 to 48 hours;
5. add client attestation;
6. enforce differentiated limits gradually.

This preserves open access while creating enough structure to detect and slow
dictionary traversal.
