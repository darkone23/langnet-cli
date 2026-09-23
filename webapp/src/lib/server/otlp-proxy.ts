import type { RequestEvent } from '@sveltejs/kit';
import {
	isOversizedOtlpBody,
	isSameOriginOtlp,
	normalizeOtlpSubPath,
	resolveOtlpUpstream
} from './otlp-upstream';

const forwardTimeoutMs = 10_000;

const forwardedRequestHeaders = ['content-type', 'content-encoding'];

export async function handleOtlpProxyPost(event: RequestEvent): Promise<Response> {
	const upstream = resolveOtlpUpstream();
	if (!upstream.enabled) {
		return otlpProxyFailure(503, 'RUM proxy disabled: OTEL_EXPORTER_OTLP_ENDPOINT is set empty\n');
	}

	const subPath = normalizeOtlpSubPath(event.params.path);
	if (subPath === null) {
		return otlpProxyFailure(404, 'OTLP path not accepted by the RUM proxy\n');
	}

	const origin = event.request.headers.get('origin');
	if (!isSameOriginOtlp(origin, event.url.origin, event.url.host)) {
		return otlpProxyFailure(403, 'Cross-origin RUM posts are not accepted\n');
	}

	const body = await event.request.arrayBuffer();
	if (isOversizedOtlpBody(event.request.headers.get('content-length'), body.byteLength)) {
		return otlpProxyFailure(413, 'RUM batch exceeds the proxy size cap\n');
	}

	const headers = new Headers();
	for (const name of forwardedRequestHeaders) {
		const value = event.request.headers.get(name);
		if (value !== null) headers.set(name, value);
	}

	let upstreamResponse: Response;
	try {
		upstreamResponse = await fetch(`${upstream.base}/${subPath}`, {
			method: 'POST',
			headers,
			body,
			signal: AbortSignal.timeout(forwardTimeoutMs)
		});
	} catch {
		return otlpProxyFailure(502, 'RUM upstream unreachable\n');
	}

	const responseBody = await upstreamResponse.arrayBuffer();
	const responseHeaders = new Headers();
	const contentType = upstreamResponse.headers.get('content-type');
	if (contentType !== null) responseHeaders.set('content-type', contentType);
	return new Response(responseBody, { status: upstreamResponse.status, headers: responseHeaders });
}

function otlpProxyFailure(status: number, message: string): Response {
	return new Response(message, {
		status,
		headers: { 'content-type': 'text/plain; charset=utf-8' }
	});
}
