import { decode, encode } from 'msgpackr';

export const msgpackContentType = 'application/msgpack';

export function serializePayload(payload: unknown) {
	return new Uint8Array(encode(payload));
}

export function deserializePayload<T = unknown>(bytes: Uint8Array | ArrayBuffer): T {
	try {
		const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
		return decode(view) as T;
	} catch (error) {
		const message = error instanceof Error ? error.message : 'unknown decode error';
		throw new Error(`MessagePack decode failed: ${message}`);
	}
}

export function requestAcceptsMsgpack(headers: Headers) {
	const accept = headers.get('accept');
	if (!accept) return false;
	return accept.split(',').some((part) => {
		const [mime, ...parameters] = part.split(';').map((value) => value.trim().toLowerCase());
		if (mime !== msgpackContentType) return false;
		return !parameters.some((parameter) => parameter === 'q=0' || parameter === 'q=0.0');
	});
}

export function payloadAcceptHeaders(headers?: HeadersInit) {
	const next = new Headers(headers);
	next.set('accept', `${msgpackContentType}, application/json`);
	return next;
}

export async function readResponsePayload<T = unknown>(response: Response): Promise<T> {
	const contentType = response.headers.get('content-type')?.split(';')[0]?.trim().toLowerCase();
	if (contentType === msgpackContentType) {
		return deserializePayload<T>(await response.arrayBuffer());
	}
	return (await response.json()) as T;
}

export async function fetchPayload<T = unknown>(input: RequestInfo | URL, init: RequestInit = {}) {
	const response = await fetch(input, {
		...init,
		headers: payloadAcceptHeaders(init.headers)
	});
	const data = await readResponsePayload<T>(response);
	return { response, data };
}
