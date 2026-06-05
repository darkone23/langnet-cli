import { isPublicWordLanguage, publicWordOfDay } from '$lib/public/word-of-day';
import { payloadResponse } from '$lib/server/msgpack-response';

export function GET({ url, request }) {
	const requestedLanguage = url.searchParams.get('language') ?? url.searchParams.get('lang');
	const language = isPublicWordLanguage(requestedLanguage) ? requestedLanguage : 'san';
	return payloadResponse(request, publicWordOfDay(language), {
		headers: {
			'cache-control': 'public, max-age=300, s-maxage=3600'
		}
	});
}
