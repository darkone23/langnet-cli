<script lang="ts">
	import { ArrowLeft, BookOpen, LibraryBig, PenLine, Telescope } from 'lucide-svelte';
	import IlluminatedSprite from '$lib/ornament/IlluminatedSprite.svelte';
	import type { ReaderAuthor, ReaderWork } from '$lib/reader';
	import {
		readerIsDeprecatedWorkRef,
		readerWorkDisplayAuthor,
		readerWorkPublicKey,
		readerWorkRef
	} from '$lib/reader';
	import { uiCopy } from '$lib/ui-copy';

	type ReaderAuthorPayload = {
		item?: ReaderAuthor | null;
		representative_works?: ReaderWork[];
		works?: ReaderWork[];
		summary?: Record<string, unknown>;
	};

	let { data } = $props();
	const initialData = () => data;
	const payload = initialData().authorPayload as ReaderAuthorPayload | null;
	const author = payload?.item ?? null;
	const works = ((initialData().works?.length
		? initialData().works
		: payload?.representative_works || payload?.works || []) ?? []) as ReaderWork[];
	const authorRef = initialData().authorRef as string;
	const loadError = initialData().loadError as string;

	function workPortalHref(workId: string) {
		return `/library/work/${encodeURIComponent(workId)}`;
	}

	function readerHref(work: ReaderWork) {
		return `/reader?work=${encodeURIComponent(readerWorkRef(work))}`;
	}

	function visibleIdentityRef(value: string | null | undefined) {
		return value && !readerIsDeprecatedWorkRef(value) ? value : '';
	}
</script>

<svelte:head>
	<title>{author?.display_name ?? authorRef} | {uiCopy.app.title}</title>
	<meta
		name="description"
		content="A source-backed author entry for reader works, identifiers, names, and provenance-oriented navigation."
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
	{:else}
		<section class="from-base-100 via-base-200 to-info/10 border-base-300 relative overflow-hidden border-b bg-[radial-gradient(circle_at_82%_18%,rgba(68,129,164,0.18),transparent_35%),linear-gradient(135deg,var(--fallback-b1,oklch(var(--b1))),var(--fallback-b2,oklch(var(--b2))))] px-6 py-14 lg:px-12 lg:py-20">
			<div class="pointer-events-none absolute top-8 right-10 hidden opacity-20 lg:block">
				<IlluminatedSprite variant="vineInitial" scale="lg" label="Memory-key vine initial ornament" />
			</div>
			<div class="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1fr_340px] lg:items-end">
				<div>
					<p class="text-info mb-4 text-sm font-bold tracking-[0.35em] uppercase">{uiCopy.readerNavigation.authorEntry}</p>
					<h1 class="max-w-5xl text-4xl leading-tight font-black tracking-tight lg:text-6xl">{author?.display_name || author?.author || authorRef}</h1>
					<p class="text-base-content/70 mt-6 max-w-3xl text-lg leading-8">
						A keyed shelf for this author: names, authority hints, and reader works before entering any individual text.
					</p>
				</div>
				<div class="bg-base-100 border-base-300 rounded-[2rem] border p-5 shadow-sm">
					<div class="flex flex-wrap gap-2">
						{#if author?.language}<span class="badge badge-info">{author.language}</span>{/if}
						{#if author?.section_key}<span class="badge badge-outline">section {author.section_key}</span>{/if}
						{#if author?.canonical_author_kind}<span class="badge badge-ghost">{author.canonical_author_kind}</span>{/if}
					</div>
					<div class="bg-base-200 mt-5 rounded-2xl p-4 text-center">
						<p class="text-3xl font-black">{author?.work_count ?? works.length}</p>
						<p class="text-base-content/55 text-xs uppercase">indexed works</p>
					</div>
				</div>
			</div>
		</section>

		<section class="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[320px_1fr] lg:px-12">
			<aside class="space-y-5">
				<article class="bg-base-100 border-base-300 rounded-[2rem] border p-6 shadow-sm">
					<div class="flex items-center gap-2">
						<PenLine class="text-secondary" size={22} />
						<h2 class="text-2xl font-black">Names and keys</h2>
					</div>
					<div class="text-base-content/65 mt-5 space-y-3 text-sm">
						<p><span class="text-base-content/50 uppercase">Display name:</span> {author?.display_name || author?.author || authorRef}</p>
						{#if author?.language}<p><span class="text-base-content/50 uppercase">Catalog language:</span> {author.language}</p>{/if}
						{#if visibleIdentityRef(author?.canonical_author_id)}<p class="break-all"><span class="text-base-content/50 uppercase">Canonical id:</span> {author?.canonical_author_id}</p>{/if}
						{#if author?.alternate_names?.length}<p><span class="text-base-content/50 uppercase">Also:</span> {author.alternate_names.join(', ')}</p>{/if}
					</div>
				</article>
			</aside>

			<section class="space-y-4">
				<div class="bg-base-100 border-base-300 rounded-[2rem] border p-6 shadow-sm">
					<div class="flex items-center gap-2">
						<LibraryBig class="text-info" size={22} />
						<h2 class="text-2xl font-black">Works in the reader</h2>
					</div>
					<p class="text-base-content/60 mt-2 text-sm">Open the work entry first for witnesses and structure, or enter the reader directly.</p>
				</div>
				{#if works.length}
					<div class="grid gap-3">
						{#each works as work}
							<article class="bg-base-100 border-base-300 rounded-[1.5rem] border p-5 shadow-sm">
								<div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
									<div class="min-w-0">
										<div class="mb-2 flex flex-wrap gap-2">
											<span class="badge badge-info">{work.language}</span>
											<span class="badge badge-outline">{work.collection_id}</span>
										</div>
										<h3 class="text-xl font-black">{work.title}</h3>
										<p class="text-base-content/60 mt-1 text-sm">{readerWorkDisplayAuthor(work)} · {readerWorkPublicKey(work)}</p>
									</div>
									<div class="flex shrink-0 gap-2">
										<a class="btn btn-sm btn-primary" href={workPortalHref(readerWorkRef(work))}>{uiCopy.readerNavigation.workEntry}</a>
										<a class="btn btn-sm btn-outline" href={readerHref(work)}><BookOpen size={16} /> Read</a>
									</div>
								</div>
							</article>
						{/each}
					</div>
				{:else}
					<div class="bg-base-100 border-base-300 rounded-[2rem] border p-8 shadow-sm">
						<h2 class="text-2xl font-black">No works returned for this author key.</h2>
						<p class="text-base-content/65 mt-3">Try the Library search with this display name; some imported rows still need stronger authority normalization.</p>
					</div>
				{/if}
			</section>
		</section>
	{/if}
</main>
