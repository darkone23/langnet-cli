<script lang="ts">
	import { ArrowLeft, BookOpen, Fingerprint, ScrollText, ShieldCheck, Telescope } from 'lucide-svelte';
	import IlluminatedSprite from '$lib/ornament/IlluminatedSprite.svelte';
	import type { ReaderSourceIndexResponse, ReaderWorkDossierResponse } from '$lib/reader';
	import {
		readerIsDeprecatedWorkRef,
		readerWorkDisplayAuthor,
		readerWorkPublicKey,
		readerWorkRef
	} from '$lib/reader';
	import { uiCopy } from '$lib/ui-copy';

	let { data } = $props();
	const initialData = () => data;
	const dossier = initialData().dossier as ReaderWorkDossierResponse | null;
	const work = dossier?.work;
	const sourceRows = (initialData().sourceRows ?? []) as ReaderSourceIndexResponse['items'];
	const workRef = initialData().workRef as string;
	const loadError = initialData().loadError as string;

	function formatNumber(value?: number | null) {
		return new Intl.NumberFormat('en-US').format(value ?? 0);
	}

	function readerHref(ref: string) {
		return `/reader?work=${encodeURIComponent(ref)}`;
	}

	function authorHref(authorId: string | null | undefined, fallback: string | null | undefined) {
		const ref = authorId || fallback;
		return ref ? `/library/author/${encodeURIComponent(ref)}` : '';
	}

	function visibleCanonicalRef(value: string | null | undefined) {
		return value && !readerIsDeprecatedWorkRef(value) ? value : '';
	}
</script>

<svelte:head>
	<title>{work?.title ?? uiCopy.readerNavigation.workEntry} | {uiCopy.app.title}</title>
	<meta
		name="description"
		content="A source-backed work entry for reader access, provenance, structure, and canonical identifiers."
	/>
</svelte:head>

<main class="orion-page bg-base-200 text-base-content min-h-screen">
	<header class="navbar border-base-300 bg-base-100/95 border-b px-4 lg:px-8">
		<div class="flex-1">
			<a href="/library" class="btn btn-sm btn-ghost">
				<ArrowLeft size={17} />
				Library
			</a>
		</div>
		<a class="btn btn-sm btn-primary" href="/reader">
			<Telescope size={17} />
			{uiCopy.readerNavigation.readerDesk}
		</a>
	</header>

	{#if loadError}
		<section class="mx-auto max-w-5xl px-6 py-12 lg:px-12">
			<div class="alert alert-error"><span>{loadError}</span></div>
		</section>
	{:else if work}
		<section class="from-base-100 via-base-200 to-warning/10 border-base-300 relative overflow-hidden border-b bg-[radial-gradient(circle_at_20%_20%,rgba(180,125,46,0.18),transparent_35%),linear-gradient(135deg,var(--fallback-b1,oklch(var(--b1))),var(--fallback-b2,oklch(var(--b2))))] px-6 py-14 lg:px-12 lg:py-20">
			<div class="pointer-events-none absolute top-8 right-8 hidden opacity-20 lg:block">
				<IlluminatedSprite variant="canonArch" scale="lg" label="Eusebian canon-table ornament" />
			</div>
			<div class="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1fr_360px] lg:items-end">
				<div>
					<p class="text-warning mb-4 text-sm font-bold tracking-[0.35em] uppercase">{uiCopy.readerNavigation.workEntry}</p>
					<h1 class="max-w-5xl text-4xl leading-tight font-black tracking-tight lg:text-6xl">{work.title}</h1>
					<p class="text-base-content/75 mt-4 text-xl">
						{#if authorHref(work.author_id, work.author)}
							<a class="link-hover link font-semibold" href={authorHref(work.author_id, work.author)}>{readerWorkDisplayAuthor(work)}</a>
						{:else}
							{readerWorkDisplayAuthor(work)}
						{/if}
					</p>
					<p class="text-base-content/70 mt-6 max-w-3xl text-lg leading-8">
						This page is the work threshold: identifiers, witnesses, divisions, and provenance before the reader enters the text.
					</p>
				</div>
				<div class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm">
					<div class="flex flex-wrap gap-2">
						<span class="badge badge-info">{work.language}</span>
						{#if work.work_kind}<span class="badge badge-ghost">{work.work_kind}</span>{/if}
					</div>
					<div class="mt-5 grid grid-cols-2 gap-3 text-center">
						<div class="bg-base-200 rounded-2xl p-4">
							<p class="text-2xl font-black">{formatNumber(work.word_count)}</p>
							<p class="text-base-content/55 text-xs uppercase">words</p>
						</div>
						<div class="bg-base-200 rounded-2xl p-4">
							<p class="text-2xl font-black">{formatNumber(dossier.summary?.structure_count)}</p>
							<p class="text-base-content/55 text-xs uppercase">divisions</p>
						</div>
					</div>
					<a class="btn btn-primary mt-5 w-full" href={readerHref(readerWorkRef(work))}>
						<BookOpen size={18} />
						{uiCopy.readerNavigation.enterReaderDesk}
					</a>
				</div>
			</div>
		</section>

		<section class="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[1fr_0.8fr] lg:px-12">
			<div class="space-y-5">
				<article class="bg-base-100 border-base-300 rounded-[2rem] border p-6 shadow-sm">
					<div class="flex items-center gap-2">
						<Fingerprint class="text-info" size={22} />
						<h2 class="text-2xl font-black">Canonical keys</h2>
					</div>
					<div class="mt-5 grid gap-3 text-sm">
						<p class="break-all"><span class="text-base-content/50 uppercase">Reader key:</span> {readerWorkPublicKey(work)}</p>
						<p><span class="text-base-content/50 uppercase">Catalog language:</span> {work.language}</p>
						{#if visibleCanonicalRef(work.canonical_text_id)}<p class="break-all"><span class="text-base-content/50 uppercase">Canonical text:</span> {work.canonical_text_id}</p>{/if}
						{#if visibleCanonicalRef(work.canonical_address) && work.canonical_address !== work.canonical_text_id}<p class="break-all"><span class="text-base-content/50 uppercase">Canonical address:</span> {work.canonical_address}</p>{/if}
					</div>
				</article>

				<article class="bg-base-100 border-base-300 rounded-[2rem] border p-6 shadow-sm">
					<div class="flex items-center gap-2">
						<ScrollText class="text-secondary" size={22} />
						<h2 class="text-2xl font-black">Table of divisions</h2>
					</div>
					{#if dossier.headings?.length}
						<div class="mt-5 grid gap-3">
							{#each dossier.headings.slice(0, 12) as heading}
								<a class="bg-base-200 hover:bg-base-300 rounded-2xl p-4 transition" href={`/reader?work=${encodeURIComponent(readerWorkRef(work))}&segment=${encodeURIComponent(heading.start_citation)}`}>
									<p class="font-black">{heading.label || heading.short_label || heading.start_citation}</p>
									<p class="text-base-content/60 mt-1 text-sm">{heading.kind} · {heading.start_citation} to {heading.end_citation}</p>
								</a>
							{/each}
						</div>
					{:else}
						<p class="text-base-content/65 mt-4">No curated division table is available yet for this work.</p>
					{/if}
				</article>
			</div>

			<aside class="space-y-5">
				<article class="bg-base-100 border-base-300 rounded-[2rem] border p-6 shadow-sm">
					<div class="flex items-center gap-2">
						<ShieldCheck class="text-success" size={22} />
						<h2 class="text-2xl font-black">Witnesses</h2>
					</div>
					{#if sourceRows.length}
						<div class="mt-5 space-y-3">
							{#each sourceRows as row}
								<div class="bg-base-200 rounded-2xl p-4 text-sm">
									<div class="flex flex-wrap gap-2">
										<span class="badge badge-outline">{row.language}</span>
										{#if row.file_status}<span class="badge badge-ghost">{row.file_status}</span>{/if}
									</div>
									<p class="mt-3 font-black">{row.edition_label || row.title || 'Witness'}</p>
									<p class="text-base-content/55 mt-2 break-all text-xs">{row.source_path}</p>
								</div>
							{/each}
						</div>
					{:else}
						<p class="text-base-content/65 mt-4">No source-index witness row was returned for this work.</p>
					{/if}
				</article>
			</aside>
		</section>
	{:else}
		<section class="mx-auto max-w-5xl px-6 py-12 lg:px-12">
			<div class="bg-base-100 border-base-300 rounded-[2rem] border p-8 shadow-sm">
				<h1 class="text-3xl font-black">Work not found.</h1>
				<p class="text-base-content/65 mt-3 break-all">{workRef}</p>
			</div>
		</section>
	{/if}
</main>
