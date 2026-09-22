import { resolveOtlpUpstream } from '$lib/server/otlp-upstream';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = () => {
	return { rumEnabled: resolveOtlpUpstream().enabled };
};
