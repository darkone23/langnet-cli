import { handleOtlpProxyPost } from '$lib/server/otlp-proxy';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = (event) => handleOtlpProxyPost(event);

const methodNotAllowed = () =>
	new Response('Method Not Allowed\n', {
		status: 405,
		headers: { allow: 'POST' }
	});

export const GET = methodNotAllowed;
export const HEAD = methodNotAllowed;
export const PUT = methodNotAllowed;
export const PATCH = methodNotAllowed;
export const DELETE = methodNotAllowed;
export const OPTIONS = methodNotAllowed;
