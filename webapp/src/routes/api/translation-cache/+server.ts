import { clearTranslationCacheFromCli } from '$lib/server/langnet-cli';
import { payloadResponse } from '$lib/server/msgpack-response';
import { searchResponseCache } from '$lib/server/search-cache';
import type { ToolId } from '$lib/search-data';

const retryableSources = new Set(['dico', 'gaffiot', 'bailly']);
const defaultMaxRetries = 3;

export async function POST({ request }) {
	const respond = (payload: unknown, init?: ResponseInit) =>
		payloadResponse(request, payload, init);
	const body = await request.json().catch(() => ({}));
	const payload = objectValue(body);
	const translationId = stringValue(payload.translation_id);
	const sourceLexicon = stringValue(payload.source_lexicon);
	const entryId = stringValue(payload.entry_id);
	const occurrence = optionalInteger(payload.occurrence);
	const headword = stringValue(payload.headword_norm);
	const sourceTextHash = stringValue(payload.source_text_hash);
	const maxRetries = optionalInteger(payload.max_retries) ?? defaultMaxRetries;

	if (!translationId && !(sourceLexicon && entryId && occurrence !== undefined && sourceTextHash)) {
		return respond(
			{ error: 'Translation retry needs a translation id or source projection metadata.' },
			{ status: 400 }
		);
	}

	if (sourceLexicon && !retryableSources.has(sourceLexicon)) {
		return respond(
			{ error: `Translation retry is not supported for ${sourceLexicon}.` },
			{ status: 400 }
		);
	}

	const result = await clearTranslationCacheFromCli({
		translationId,
		sourceLexicon: sourceLexicon as ToolId | undefined,
		entryId,
		occurrence,
		headword,
		sourceTextHash,
		retryReason: 'user_rejected',
		maxRetries,
		timeoutMs: optionalInteger(payload.timeout_ms) ?? 30_000
	});
	searchResponseCache.clear();

	const status = booleanValue(result.limit_reached) ? 429 : 200;
	return respond(result, { status });
}

function objectValue(value: unknown): Record<string, unknown> {
	return value && typeof value === 'object' && !Array.isArray(value)
		? (value as Record<string, unknown>)
		: {};
}

function stringValue(value: unknown) {
	return typeof value === 'string' ? value.trim() : '';
}

function booleanValue(value: unknown) {
	return value === true;
}

function optionalInteger(value: unknown) {
	if (typeof value === 'number' && Number.isInteger(value)) return value;
	if (typeof value !== 'string' || !value.trim()) return undefined;
	const parsed = Number.parseInt(value, 10);
	return Number.isFinite(parsed) ? parsed : undefined;
}
