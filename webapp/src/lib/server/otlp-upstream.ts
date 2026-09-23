export const defaultOtlpUpstreamBase = 'http://signoz.elf-lizard.ts.net:4318';

export type OtlpUpstream = { enabled: true; base: string } | { enabled: false };

export type OtlpProxyEnv = { OTEL_EXPORTER_OTLP_ENDPOINT?: string | undefined };

export const allowedOtlpPaths = new Set(['v1/traces', 'v1/metrics']);

export const maxOtlpProxyBodyBytes = 2 * 1024 * 1024;

export function resolveOtlpUpstream(env: OtlpProxyEnv = process.env): OtlpUpstream {
	const raw = env.OTEL_EXPORTER_OTLP_ENDPOINT;
	if (raw === undefined) {
		return { enabled: true, base: defaultOtlpUpstreamBase };
	}
	const base = raw.trim().replace(/\/+$/, '');
	if (!base || !isHttpUrl(base)) {
		return { enabled: false };
	}
	return { enabled: true, base };
}

export function isHttpUrl(value: string): boolean {
	try {
		const url = new URL(value);
		return url.protocol === 'http:' || url.protocol === 'https:';
	} catch {
		return false;
	}
}

export function normalizeOtlpSubPath(value: string | undefined): string | null {
	const joined = (value ?? '').split('/').filter(Boolean).join('/');
	return allowedOtlpPaths.has(joined) ? joined : null;
}

export function isSameOriginOtlp(
	origin: string | null,
	requestOrigin: string,
	requestHost: string
): boolean {
	if (typeof origin !== 'string' || origin.length === 0) return false;
	if (origin === requestOrigin) return true;
	try {
		return new URL(origin).host === requestHost;
	} catch {
		return false;
	}
}

export function isOversizedOtlpBody(contentLength: string | null, byteLength: number): boolean {
	if (byteLength > maxOtlpProxyBodyBytes) return true;
	if (contentLength !== null) {
		const declared = Number(contentLength);
		if (Number.isFinite(declared) && declared > maxOtlpProxyBodyBytes) return true;
	}
	return false;
}
