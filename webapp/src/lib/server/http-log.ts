type HttpRequestLogInput = {
	method: string;
	path: string;
	status: number;
	durationMs: number;
};

export function httpRequestLoggingEnabled(value = process.env.LANGNET_HTTP_LOG) {
	return ['1', 'true', 'yes', 'on'].includes((value ?? '').trim().toLowerCase());
}

export function formatHttpRequestLog({ method, path, status, durationMs }: HttpRequestLogInput) {
	return `[http] ${method} ${path} ${status} ${durationMs.toFixed(1)}ms`;
}
