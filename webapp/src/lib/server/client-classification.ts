import type { AttestationStatus } from './client-attestation';

export type ClientClass = 'trusted_web_session' | 'anonymous_unattested' | 'suspicious';

export type ClientClassification = {
	clientClass: ClientClass;
	reason: string;
};

type ScannerRequest = {
	path: string;
	attestationStatus: AttestationStatus;
	anonymousSessionId?: string;
	userAgent: string;
};

export function classifyClient(input: ScannerRequest): ClientClassification {
	if (
		input.path === '/xmlrpc.php' ||
		input.path.startsWith('/xmlrpc.php') ||
		input.path.startsWith('/wp-admin')
	) {
		return {
			clientClass: 'suspicious',
			reason: 'scanner-path'
		};
	}

	if (!input.anonymousSessionId) {
		return {
			clientClass: 'anonymous_unattested',
			reason: 'missing-session'
		};
	}

	if (input.attestationStatus === 'valid') {
		return {
			clientClass: 'trusted_web_session',
			reason: 'valid-attestation'
		};
	}

	return {
		clientClass: 'anonymous_unattested',
		reason: `attestation-${input.attestationStatus}`
	};
}
