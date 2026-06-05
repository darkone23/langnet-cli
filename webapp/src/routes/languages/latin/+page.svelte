<script lang="ts">
	import { ScrollText } from 'lucide-svelte';
	import LanguagePage from '$lib/public/LanguagePage.svelte';
	import { uiCopy } from '$lib/ui-copy';

	const copy = {
		...uiCopy.publicSite.languages.lat,
		language: 'lat' as const,
		accentText: 'text-warning',
		accentTo: 'to-warning/10',
		Icon: ScrollText
	};
</script>

<LanguagePage {copy} />
