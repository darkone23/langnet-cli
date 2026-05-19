import { paradigmPayloadHasForms, sanskritParadigmLemmaFallbacks } from '$lib/paradigm-ui';
import { payloadResponse } from '$lib/server/msgpack-response';
import { languageModes, type LanguageMode } from '$lib/search-data';
import { paradigmFromCli } from '$lib/server/langnet-cli';

const validLanguages = new Set(languageModes.map(({ id }) => id));
const validKinds = new Set(['declension', 'conjugation']);

export async function GET({ url, request }) {
	const respond = (payload: unknown, init?: ResponseInit) =>
		payloadResponse(request, payload, init);
	const requestedLanguage = url.searchParams.get('language') ?? 'san';
	const language = validLanguages.has(requestedLanguage as LanguageMode)
		? (requestedLanguage as LanguageMode)
		: 'san';
	const lemma = (url.searchParams.get('lemma') ?? '').trim();
	const requestedKind = url.searchParams.get('kind') ?? 'declension';
	const kind = validKinds.has(requestedKind) ? requestedKind : 'declension';
	const gender = url.searchParams.get('gender') ?? undefined;
	const presentClass = url.searchParams.get('class') ?? undefined;

	if (!lemma) {
		return respond(
			{
				schema_version: 'langnet.paradigm.v1',
				language,
				lemma,
				kind,
				source: '',
				source_request: {},
				paradigms: [],
				warnings: [],
				error: 'Paradigm lookup needs a lemma.'
			},
			{ status: 400 }
		);
	}

	try {
		let firstPayload: Awaited<ReturnType<typeof paradigmFromCli>> | null = null;
		let lastError: unknown = null;
		const lemmas = language === 'san' ? sanskritParadigmLemmaFallbacks(lemma) : [lemma];

		for (const requestLemma of lemmas) {
			try {
				const payload = await paradigmFromCli({
					language,
					lemma: requestLemma,
					kind,
					gender,
					presentClass,
					timeoutMs: readInteger(url.searchParams.get('timeout_ms'), 120_000, 1_000, 300_000)
				});

				firstPayload ??= payload;
				if (paradigmPayloadHasForms(payload)) return respond(payload);
			} catch (error) {
				lastError = error;
			}
		}

		if (firstPayload) return respond(firstPayload);
		throw lastError;
	} catch (error) {
		return respond(
			{
				schema_version: 'langnet.paradigm.v1',
				language,
				lemma,
				kind,
				source: '',
				source_request: {},
				paradigms: [],
				warnings: [],
				error: error instanceof Error ? error.message : 'Paradigm lookup failed.'
			},
			{ status: 502 }
		);
	}
}

function readInteger(value: string | null, fallback: number, min: number, max: number) {
	if (!value) return fallback;
	const parsed = Number.parseInt(value, 10);
	if (!Number.isFinite(parsed)) return fallback;
	return Math.min(max, Math.max(min, parsed));
}
