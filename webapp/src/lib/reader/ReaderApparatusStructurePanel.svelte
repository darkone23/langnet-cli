<script lang="ts">
	import ReaderCanonTable from './ReaderCanonTable.svelte';
	import type { ReaderStructureNode } from '$lib/reader';

	type Props = {
		structure: ReaderStructureNode[];
		onOpenDivision: (workId: string, citation: string) => void;
	};

	let { structure, onOpenDivision }: Props = $props();
</script>

<ReaderCanonTable items={structure} {onOpenDivision} />
