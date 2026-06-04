type HttpRequestLogInput = {
	method: string;
	path: string;
	status: number;
	durationMs: number;
	clientIp?: string;
	clientIpSource?: string;
	cfRay?: string;
	cfCountry?: string;
	userAgent?: string;
	referer?: string;
	clientClass?: string;
	attestationStatus?: string;
	attestationScope?: string;
	requestScope?: string;
	tokenScope?: string;
	requestCostScore?: number;
	dictionary?: string;
	language?: string;
	translation?: string;
	queryPresent?: boolean;
	crawlerDisallowedRoute?: boolean;
	crawlerBot?: string;
	crawlerPolicyReason?: string;
	rateLimitDecision?: {
		mode: string;
		wouldLimit: boolean;
		keyType: string;
		bucket: string;
		limit: number;
		remaining: number;
		used: number;
		windowSeconds: number;
	};
};

export function httpRequestLoggingEnabled(value = process.env.LANGNET_HTTP_LOG) {
	return ['1', 'true', 'yes', 'on'].includes((value ?? '').trim().toLowerCase());
}

type LogfmtValue = string | number | boolean | undefined | null;

function logfmtValue(value: string): string {
	if (value === '') {
		return '""';
	}

	if (/[\s="\\]/.test(value)) {
		const escaped = value
			.replaceAll('\\', '\\\\')
			.replaceAll('"', '\\"')
			.replaceAll('\n', '\\n')
			.replaceAll('\r', '\\r')
			.replaceAll('\t', '\\t');
		return `"${escaped}"`;
	}

	return value;
}

export function formatLogfmt(fields: Record<string, LogfmtValue>) {
	const parts = Object.entries(fields)
		.map(([key, value]) => {
			if (value === undefined || value === null) return null;
			if (typeof value === 'boolean') return `${key}=${value.toString()}`;
			if (typeof value === 'number') return `${key}=${value}`;
			if (typeof value === 'string') {
				if (!value) return null;
				return `${key}=${logfmtValue(value)}`;
			}
			return null;
		})
		.filter((entry): entry is string => typeof entry === 'string');
	return parts.join(' ');
}

export function formatHttpRequestLog({
	method,
	path,
	status,
	durationMs,
	clientIp,
	cfRay,
	cfCountry,
	clientIpSource,
	userAgent,
	referer,
	clientClass,
	attestationStatus,
	attestationScope,
	requestScope,
	tokenScope,
	requestCostScore,
	dictionary,
	language,
	translation,
	queryPresent,
	crawlerDisallowedRoute,
	crawlerBot,
	crawlerPolicyReason,
	rateLimitDecision
}: HttpRequestLogInput) {
	const roundedDurationMs = Number.isFinite(durationMs) ? Number(durationMs.toFixed(1)) : 0;
	return formatLogfmt({
		event: 'http_request',
		method,
		path,
		status,
		duration_ms: roundedDurationMs,
		client_ip: clientIp,
		client_ip_source: clientIpSource,
		cf_ray: cfRay,
		cf_country: cfCountry,
		client_class: clientClass,
		attestation_status: attestationStatus,
		attestation_scope: attestationScope,
		request_scope: requestScope,
		token_scope: tokenScope,
		request_cost: requestCostScore,
		lang: language,
		dictionary,
		translation,
		query: queryPresent,
		crawler_disallowed_route: crawlerDisallowedRoute,
		crawler_bot: crawlerBot,
		crawler_policy_reason: crawlerPolicyReason,
		ua: userAgent,
		referer,
		rate_limit_mode: rateLimitDecision?.mode,
		rate_limit_would_limit: rateLimitDecision?.wouldLimit,
		rate_limit_key_type: rateLimitDecision?.keyType,
		rate_limit_bucket: rateLimitDecision?.bucket,
		rate_limit_limit: rateLimitDecision?.limit,
		rate_limit_remaining: rateLimitDecision?.remaining,
		rate_limit_used: rateLimitDecision?.used,
		rate_limit_window_seconds: rateLimitDecision?.windowSeconds
	});
}
