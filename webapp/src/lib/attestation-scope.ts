export const unknownScope = 'unknown_api';

export type AttestationScope =
	| 'search'
	| 'word_index'
	| 'reader'
	| 'paradigm'
	| 'motd'
	| 'translation_cache'
	| 'encounter_briefing'
	| 'unknown_api';

export type RequestScope = AttestationScope | 'page_view' | 'static_asset' | 'healthcheck';

export function isAuthPath(pathname: string) {
	return pathname === '/api/auth' || pathname.startsWith('/api/auth/');
}

export function isHealthPath(pathname: string) {
	return pathname === '/api/health';
}

export function attestationScopeFromPath(pathname: string): AttestationScope {
	if (isAuthPath(pathname)) return 'unknown_api';
	if (isHealthPath(pathname)) return 'unknown_api';
	switch (pathname) {
		case '/api/search':
			return 'search';
		case '/api/word-index':
			return 'word_index';
		case '/api/reader':
			return 'reader';
		case '/api/paradigm':
			return 'paradigm';
		case '/api/motd':
			return 'motd';
		case '/api/translation-cache':
			return 'translation_cache';
		case '/api/encounter-briefing':
			return 'encounter_briefing';
		default:
			return 'unknown_api';
	}
}

export function isAttestablePath(pathname: string) {
	return pathname.startsWith('/api/') && !isAuthPath(pathname) && !isHealthPath(pathname);
}

export function requestScopeFromPath({
	pathname,
	clientIp: _clientIp,
	userAgent: _userAgent
}: {
	pathname: string;
	clientIp?: string;
	userAgent?: string;
}): RequestScope {
	if (isHealthPath(pathname)) return 'healthcheck';
	if (isAttestablePath(pathname)) return attestationScopeFromPath(pathname);
	if (isStaticAssetPath(pathname)) return 'static_asset';
	if (!pathname.startsWith('/api/')) return 'page_view';
	return 'unknown_api';
}

function isStaticAssetPath(pathname: string) {
	return (
		pathname.startsWith('/_app/') ||
		pathname === '/favicon.ico' ||
		pathname === '/robots.txt' ||
		pathname.endsWith('.css') ||
		pathname.endsWith('.js') ||
		pathname.endsWith('.map') ||
		pathname.endsWith('.png') ||
		pathname.endsWith('.jpg') ||
		pathname.endsWith('.jpeg') ||
		pathname.endsWith('.svg') ||
		pathname.endsWith('.webp') ||
		pathname.endsWith('.woff') ||
		pathname.endsWith('.woff2')
	);
}
