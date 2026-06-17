import { readerSourceIndex, readerWorkDossier } from '$lib/server/reader-cli';

export async function load({ params, url }) {
	const work = decodeURIComponent(params.work);
	const catalogId = url.searchParams.get('catalog');
	try {
		const [dossier, sourceIndex] = await Promise.all([
			readerWorkDossier({ catalogId, work, options: { timeoutMs: 300_000 } }),
			readerSourceIndex({
				catalogId,
				workId: work,
				limit: 8,
				options: { timeoutMs: 300_000 }
			})
		]);
		return {
			workRef: work,
			dossier,
			sourceRows: sourceIndex.items ?? [],
			loadError: ''
		};
	} catch (cause) {
		return {
			workRef: work,
			dossier: null,
			sourceRows: [],
			loadError: cause instanceof Error ? cause.message : 'Unable to load the work entry.'
		};
	}
}
