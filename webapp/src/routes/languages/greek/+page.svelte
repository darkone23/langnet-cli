<script lang="ts">
	import { Omega } from 'lucide-svelte';
	import LanguagePage from '$lib/public/LanguagePage.svelte';
	import { uiCopy } from '$lib/ui-copy';

	const copy = {
		...uiCopy.publicSite.languages.grc,
		language: 'grc' as const,
		accentText: 'text-info',
		accentTo: 'to-info/10',
		Icon: Omega
	};
</script>

<LanguagePage {copy} />
