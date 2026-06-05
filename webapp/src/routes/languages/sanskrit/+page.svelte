<script lang="ts">
	import { Flower2 } from 'lucide-svelte';
	import LanguagePage from '$lib/public/LanguagePage.svelte';
	import { uiCopy } from '$lib/ui-copy';

	const copy = {
		...uiCopy.publicSite.languages.san,
		language: 'san' as const,
		accentText: 'text-success',
		accentTo: 'to-success/10',
		Icon: Flower2
	};
</script>

<LanguagePage {copy} />
