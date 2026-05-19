import { json } from '@sveltejs/kit';
import { msgpackContentType, requestAcceptsMsgpack, serializePayload } from '$lib/msgpack';

export function payloadResponse(request: Request, payload: unknown, init: ResponseInit = {}) {
	if (!requestAcceptsMsgpack(request.headers)) return json(payload, init);

	const headers = new Headers(init.headers);
	headers.set('content-type', msgpackContentType);
	headers.set('vary', appendVary(headers.get('vary'), 'Accept'));
	return new Response(serializePayload(payload), {
		...init,
		headers
	});
}

function appendVary(value: string | null, header: string) {
	if (!value) return header;
	const parts = value.split(',').map((part) => part.trim());
	if (parts.some((part) => part.toLowerCase() === header.toLowerCase())) return value;
	return [...parts, header].join(', ');
}
