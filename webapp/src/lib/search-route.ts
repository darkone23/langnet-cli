import type { TranslationMode } from './search-data';

export function shouldRetrySearchWithoutTranslation(error: unknown, mode: TranslationMode) {
	if (mode === 'off') return false;
	const message = searchErrorMessage(error).toLowerCase();
	return (
		message.includes('translation cache') ||
		message.includes('translation block') ||
		message.includes('kept french dictionary prose')
	);
}

export function searchErrorMessage(error: unknown) {
	return error instanceof Error ? error.message : 'Live CLI search failed.';
}
