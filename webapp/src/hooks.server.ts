import type { Handle } from '@sveltejs/kit';
import { appendRequestCostHeaders, requestCostFromUrl } from '$lib/server/request-cost';
import { classifyClient } from '$lib/server/client-classification';
import { verifyAttestationToken } from '$lib/server/client-attestation';
import { getOrCreateAnonymousSession } from '$lib/server/anonymous-session';
import {
	attestationScopeFromPath,
	isAttestablePath,
	isHealthPath,
	requestScopeFromPath
} from '$lib/attestation-scope';
import { requestIdentityFromHeaders } from '$lib/server/request-identity';
import { getRateLimitDecision, type RateLimitDecision } from '$lib/server/rate-limit';
import { formatHttpRequestLog, httpRequestLoggingEnabled } from '$lib/server/http-log';
import { observeRateLimitRequest } from '$lib/server/rate-limit-rollup';
import { getCrawlerDisallowedRouteDecision } from '$lib/server/crawler-route-policy';

const logHttpRequests = httpRequestLoggingEnabled();

export const handle: Handle = async ({ event, resolve }) => {
	const startedAt = performance.now();
	let status = 500;
	const requestIdentity = requestIdentityFromHeaders(
		event.request.headers,
		event.getClientAddress()
	);
	const requestScope = requestScopeFromPath({
		pathname: event.url.pathname,
		clientIp: requestIdentity.clientIp,
		userAgent: requestIdentity.userAgent
	});
	const responseLogMetadata = buildRequestMetadata(event.url, undefined, requestScope);
	const crawlerDisallowedRoute = getCrawlerDisallowedRouteDecision({
		pathname: event.url.pathname,
		search: event.url.search,
		clientIp: requestIdentity.clientIp,
		userAgent: requestIdentity.userAgent
	});

	if (isHealthPath(event.url.pathname)) {
		try {
			const response = crawlerDisallowedRoute.block
				? new Response('Forbidden: crawlers are not authorized to use API endpoints.\n', {
						status: 403,
						headers: {
							'content-type': 'text/plain; charset=utf-8',
							'x-robots-tag': 'noindex, nofollow'
						}
					})
				: await resolve(event);
			status = response.status;
			return response;
		} finally {
			if (logHttpRequests) {
				const path = `${event.url.pathname}${event.url.search}`;
				console.info(
					formatHttpRequestLog({
						method: event.request.method,
						path,
						status,
						durationMs: performance.now() - startedAt,
						clientIp: requestIdentity.clientIp,
						cfRay: requestIdentity.cfRay,
						cfCountry: requestIdentity.cfCountry,
						userAgent: requestIdentity.userAgent,
						referer: requestIdentity.referer,
						crawlerDisallowedRoute: crawlerDisallowedRoute.block || undefined,
						crawlerBot: crawlerDisallowedRoute.botName,
						crawlerPolicyReason: crawlerDisallowedRoute.reason,
						...responseLogMetadata
					})
				);
			}
		}
	}

	const requestCost = requestCostFromUrl(event.url);
	const anonymousSession = getOrCreateAnonymousSession(event.cookies);
	const attestationScope = isAttestablePath(event.url.pathname)
		? attestationScopeFromPath(event.url.pathname)
		: undefined;
	const attestation =
		attestationScope === undefined
			? { status: 'missing' as const }
			: verifyAttestationToken({
					token: event.request.headers.get('X-LangNet-Client-Attestation') ?? undefined,
					sessionId: anonymousSession.id,
					scope: attestationScope,
					secret: process.env.LANGNET_CLIENT_ATTESTATION_SECRET
				});
	const clientClassification = classifyClient({
		path: event.url.pathname,
		attestationStatus: attestation.status,
		anonymousSessionId: anonymousSession.id,
		userAgent: requestIdentity.userAgent
	});
	const rateLimitDecision: RateLimitDecision = getRateLimitDecision({
		clientClass: clientClassification.clientClass,
		requestCost,
		attestationScope,
		requestScope,
		anonymousSessionId: anonymousSession.id,
		clientIp: requestIdentity.clientIp
	});
	event.locals.anonymousSessionId = anonymousSession.id;
	event.locals.requestIdentity = requestIdentity;
	event.locals.requestCost = requestCost;
	event.locals.clientClassification = clientClassification;
	event.locals.clientAttestation = attestation;
	event.locals.rateLimitDecision = rateLimitDecision;
	const responseLogMetadataWithAttestationScope = buildRequestMetadata(
		event.url,
		attestationScope,
		requestScope
	);

	try {
		const response = crawlerDisallowedRoute.block
			? new Response('Forbidden: crawlers are not authorized to use API endpoints.\n', {
					status: 403,
					headers: {
						'content-type': 'text/plain; charset=utf-8',
						'x-robots-tag': 'noindex, nofollow'
					}
				})
			: await resolve(event);
		status = response.status;
		appendRequestCostHeaders(response.headers, requestCost);
		response.headers.set('LangNet-Client-Class', clientClassification.clientClass);
		response.headers.set('LangNet-Attestation', attestation.status);
		response.headers.set('LangNet-RateLimit-Mode', rateLimitDecision.mode);
		response.headers.set('LangNet-RateLimit-Would-Limit', String(rateLimitDecision.wouldLimit));
		response.headers.set('LangNet-RateLimit-Key-Type', rateLimitDecision.keyType);
		response.headers.set('LangNet-RateLimit-Bucket', rateLimitDecision.bucket);
		response.headers.set('LangNet-RateLimit-Limit', String(rateLimitDecision.limit));
		response.headers.set('LangNet-RateLimit-Remaining', String(rateLimitDecision.remaining));
		response.headers.set('LangNet-RateLimit-Window-Seconds', String(rateLimitDecision.windowSeconds));
		if (attestationScope) {
			response.headers.set('LangNet-Attestation-Scope', attestationScope);
		}
		response.headers.append(
			'server-timing',
			`app;dur=${(performance.now() - startedAt).toFixed(1)}`
		);
		return response;
	} finally {
		if (logHttpRequests) {
			const path = `${event.url.pathname}${event.url.search}`;

			console.info(
				formatHttpRequestLog({
					method: event.request.method,
					path,
					status,
					durationMs: performance.now() - startedAt,
					clientIp: requestIdentity.clientIp,
					cfRay: requestIdentity.cfRay,
					cfCountry: requestIdentity.cfCountry,
					userAgent: requestIdentity.userAgent,
					referer: requestIdentity.referer,
					clientClass: clientClassification.clientClass,
					attestationStatus: attestation.status,
					requestCostScore: requestCost.score,
					clientIpSource: requestIdentity.clientIpSource,
					tokenScope: event.locals.tokenScope,
					rateLimitDecision: event.locals.rateLimitDecision,
					crawlerDisallowedRoute: crawlerDisallowedRoute.block || undefined,
					crawlerBot: crawlerDisallowedRoute.botName,
					crawlerPolicyReason: crawlerDisallowedRoute.reason,
					...responseLogMetadataWithAttestationScope
				})
			);
		}
			try {
				const principal =
					rateLimitDecision.keyType === 'anonymous_session'
						? anonymousSession.id
						: requestIdentity.clientIp;
				const rollupAttestationScope = attestationScope ?? requestScope;
				observeRateLimitRequest({
					observedAtEpochSeconds: Math.floor(Date.now() / 1000),
					status,
					requestCost: requestCost.score,
					clientClass: clientClassification.clientClass,
					attestationStatus: attestation.status,
					attestationScope: rollupAttestationScope,
					rateLimitDecision,
					keyType: rateLimitDecision.keyType,
					principal
				});
		} catch {
			// Observation storage must never impact request handling.
		}
	}
};

function buildRequestMetadata(url: URL, attestationScope: string | undefined, requestScope: string) {
	const dictionary = readQueryValue(url, 'source', 'dictionary');
	const language = readQueryValue(url, 'language', 'lang');
	const translation = readQueryValue(url, 'translation');
	return {
		attestationScope,
		requestScope,
		dictionary: dictionary ?? undefined,
		language: language ?? undefined,
		translation: translation ?? undefined,
		queryPresent: Boolean(url.searchParams.get('q') || url.searchParams.get('query'))
	};
}

function readQueryValue(url: URL, ...keys: string[]) {
	for (const key of keys) {
		const value = url.searchParams.get(key);
		if (value) return value;
	}
	return null;
}
