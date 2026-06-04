const unknown = 'unknown';

export type RequestIdentity = {
	clientIp: string;
	clientIpSource: 'cf-connecting-ip' | 'x-forwarded-for' | 'event-client-address' | 'unknown';
	cfConnectingIp?: string;
	cfRay?: string;
	cfCountry?: string;
	userAgent: string;
	referer: string;
};

export function requestIdentityFromHeaders(
	headers: Headers,
	clientAddress?: string
): RequestIdentity {
	const cfConnectingIp = headers.get('cf-connecting-ip')?.trim() ?? '';
	const xForwardedFor = headers.get('x-forwarded-for')?.trim() ?? '';
	const firstProxyIp = xForwardedFor
		.split(',')
		.map((candidate) => candidate.trim())
		.find((candidate) => candidate.length > 0);

	let clientIp = unknown;
	let clientIpSource: RequestIdentity['clientIpSource'] = 'unknown';

	if (cfConnectingIp) {
		clientIp = cfConnectingIp;
		clientIpSource = 'cf-connecting-ip';
	} else if (firstProxyIp) {
		clientIp = firstProxyIp;
		clientIpSource = 'x-forwarded-for';
	} else if (clientAddress) {
		clientIp = clientAddress;
		clientIpSource = 'event-client-address';
	}

	return {
		clientIp,
		clientIpSource,
		cfConnectingIp: cfConnectingIp || undefined,
		cfRay: headers.get('cf-ray')?.trim() || undefined,
		cfCountry: headers.get('cf-ipcountry')?.trim() || undefined,
		userAgent: headers.get('user-agent') ?? '',
		referer: headers.get('referer') ?? ''
	};
}
