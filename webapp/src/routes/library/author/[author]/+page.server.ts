import { readerAuthor, readerWorks } from '$lib/server/reader-cli';
import type { LanguageMode } from '$lib/search-data';

export async function load({ params, url }) {
	const author = decodeURIComponent(params.author);
	const catalogId = url.searchParams.get('catalog');
	const language = readLanguage(url.searchParams.get('language') ?? url.searchParams.get('lang'));
	try {
		const [authorPayload, worksPayload] = await Promise.all([
			readerAuthor({ catalogId, language, author, representativeLimit: 12, options: { timeoutMs: 300_000 } }),
			readerWorks({
				catalogId,
				language,
				authorId: author,
				limit: 24,
				sort: 'global-popularity',
				options: { timeoutMs: 300_000 }
			})
		]);
		return {
			authorRef: author,
			authorPayload,
			works: worksPayload.items ?? [],
			loadError: ''
		};
	} catch (cause) {
		return {
			authorRef: author,
			authorPayload: null,
			works: [],
			loadError: cause instanceof Error ? cause.message : 'Unable to load the author entry.'
		};
	}
}

function readLanguage(value: string | null): LanguageMode | undefined {
	return value === 'lat' || value === 'grc' || value === 'san' ? value : undefined;
}
