// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			anonymousSessionId?: string;
			requestIdentity?: import('$lib/server/request-identity').RequestIdentity;
			requestCost?: import('$lib/server/request-cost').RequestCost;
			clientClassification?: import('$lib/server/client-classification').ClientClassification;
			clientAttestation?: import('$lib/server/client-attestation').AttestationResult;
			tokenScope?: import('$lib/attestation-scope').AttestationScope;
			rateLimitDecision?: import('$lib/server/rate-limit').RateLimitDecision;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
