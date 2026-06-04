import { redirect } from '@sveltejs/kit';

const legacyDeskParams = new Set([
	'q',
	'query',
	'lang',
	'language',
	'dictionary',
	'source',
	'translation',
	'backend',
	'theme',
	'load',
	'visible'
]);

export function load({ url }) {
	if ([...legacyDeskParams].some((key) => url.searchParams.has(key))) {
		redirect(308, `/q?${url.searchParams.toString()}`);
	}
}
