type CrawlerDisallowedRouteInput = {
	pathname: string;
	search: string;
	clientIp: string;
	userAgent: string;
};

export type CrawlerDisallowedRouteDecision = {
	block: boolean;
	botName?: 'googlebot';
	reason?: 'crawler-disallowed-route';
};

const googleCrawlerIpv4Cidrs = [
	'64.233.160.0/19',
	'66.102.0.0/20',
	'66.249.0.0/16',
	'72.14.192.0/18',
	'74.125.0.0/16',
	'209.85.128.0/17',
	'216.239.32.0/19'
].map(parseIpv4Cidr);

export function getCrawlerDisallowedRouteDecision(
	input: CrawlerDisallowedRouteInput
): CrawlerDisallowedRouteDecision {
	if (!isCrawlerDisallowedRoute(input.pathname, input.search)) {
		return { block: false };
	}

	if (!isGooglebotUserAgent(input.userAgent)) {
		return { block: false };
	}

	if (!isIpv4InCidrs(input.clientIp, googleCrawlerIpv4Cidrs)) {
		return { block: false };
	}

	return {
		block: true,
		botName: 'googlebot',
		reason: 'crawler-disallowed-route'
	};
}

function isCrawlerDisallowedRoute(pathname: string, search: string) {
	if (pathname.startsWith('/api/')) return true;
	if (pathname === '/q' || pathname.startsWith('/q/')) return true;
	if (pathname === '/reader' || pathname.startsWith('/reader/')) return true;

	if (pathname === '/' && search) {
		const params = new URLSearchParams(search);
		return ['q', 'query', 'lang', 'language', 'dictionary', 'source', 'translation'].some((key) =>
			params.has(key)
		);
	}

	return false;
}

function isGooglebotUserAgent(userAgent: string) {
	return /\bGooglebot\b/i.test(userAgent);
}

type ParsedIpv4Cidr = {
	base: number;
	mask: number;
};

function parseIpv4Cidr(cidr: string): ParsedIpv4Cidr {
	const [address, prefixLengthRaw] = cidr.split('/');
	const prefixLength = Number(prefixLengthRaw);
	const base = parseIpv4(address);
	if (base === undefined || !Number.isInteger(prefixLength) || prefixLength < 0 || prefixLength > 32) {
		throw new Error(`Invalid IPv4 CIDR: ${cidr}`);
	}
	const mask = prefixLength === 0 ? 0 : (0xffffffff << (32 - prefixLength)) >>> 0;
	return {
		base: base & mask,
		mask
	};
}

function isIpv4InCidrs(ip: string, cidrs: ParsedIpv4Cidr[]) {
	const parsedIp = parseIpv4(ip);
	if (parsedIp === undefined) return false;
	return cidrs.some((cidr) => (parsedIp & cidr.mask) === cidr.base);
}

function parseIpv4(ip: string): number | undefined {
	const octets = ip.split('.');
	if (octets.length !== 4) return undefined;

	let value = 0;
	for (const octet of octets) {
		if (!/^\d{1,3}$/.test(octet)) return undefined;
		const parsed = Number(octet);
		if (!Number.isInteger(parsed) || parsed < 0 || parsed > 255) return undefined;
		value = (value << 8) + parsed;
	}

	return value >>> 0;
}
