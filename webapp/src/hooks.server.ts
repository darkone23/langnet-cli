import type { Handle } from '@sveltejs/kit';
import { formatHttpRequestLog, httpRequestLoggingEnabled } from '$lib/server/http-log';

const logHttpRequests = httpRequestLoggingEnabled();

export const handle: Handle = async ({ event, resolve }) => {
	const startedAt = performance.now();
	let status = 500;

	try {
		const response = await resolve(event);
		status = response.status;
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
					durationMs: performance.now() - startedAt
				})
			);
		}
	}
};
