<script lang="ts">
	import IlluminatedSprite from '$lib/ornament/IlluminatedSprite.svelte';

	const specimens = [
		{
			variant: 'beast',
			title: 'Marginal beast',
			note: 'Cute marginal monster with visible construction, foliate ruff, readable eyes, paws, tail, and sketch contour.'
		},
		{
			variant: 'canonArch',
			title: 'Canon-table arch',
			note: 'Bounded arcade with column grid, arch compass, tabular rules, spandrels, and rubric witnesses.'
		},
		{
			variant: 'vineInitial',
			title: 'Vine initial',
			note: 'Inhabited initial whose leaves, veins, rubrics, and bowls follow the letter construction.'
		}
	] as const;
</script>

<svelte:head>
	<title>Ornament zoo | Project Orion</title>
	<meta
		name="description"
		content="A diagnostic page for Project Orion illuminated manuscript ornaments."
	/>
</svelte:head>

<main class="orion-zoo">
	<header class="orion-zoo__header">
		<p>Project Orion ornament study</p>
		<h1>Illuminated sprite zoo</h1>
		<span>
			A screenshot-friendly review sheet for manuscript pets, canon tables, and memory initials.
		</span>
	</header>

	<section class="orion-zoo__principles" aria-label="Ornament design principles">
		<article>
			<strong>Model-book geometry</strong>
			<span>Every ornament should reveal a Villard-like armature: arcs, axes, triangles, columns, or measured bowls.</span>
		</article>
		<article>
			<strong>Thumbnail silhouette</strong>
			<span>The creature, table, and initial must remain intelligible at the smallest review size.</span>
		</article>
		<article>
			<strong>Manuscript register</strong>
			<span>Linework should feel drawn, rubricated, and architectural rather than like rounded SaaS iconography.</span>
		</article>
	</section>

	<section class="orion-zoo__grid" aria-label="Illuminated sprite specimens">
		{#each specimens as specimen}
			<article class="orion-zoo__card">
				<div class="orion-zoo__copy">
					<p>{specimen.title}</p>
					<span>{specimen.note}</span>
				</div>
				<div class="orion-zoo__stage orion-zoo__stage--large">
					<IlluminatedSprite
						variant={specimen.variant}
						scale="lg"
						label={`${specimen.title} large specimen`}
					/>
				</div>
				<div class="orion-zoo__sizes">
					<div>
						<IlluminatedSprite
							variant={specimen.variant}
							scale="sm"
							label={`${specimen.title} small specimen`}
						/>
						<span>small</span>
					</div>
					<div>
						<IlluminatedSprite
							variant={specimen.variant}
							scale="md"
							label={`${specimen.title} medium specimen`}
						/>
						<span>medium</span>
					</div>
					<div>
						<IlluminatedSprite
							variant={specimen.variant}
							scale="lg"
							label={`${specimen.title} large specimen duplicate`}
						/>
						<span>large</span>
					</div>
				</div>
			</article>
		{/each}
	</section>
</main>

<style>
	.orion-zoo {
		min-height: 100vh;
		background:
			radial-gradient(circle at 12% 10%, rgba(154, 92, 31, 0.18), transparent 20rem),
			radial-gradient(circle at 86% 22%, rgba(29, 75, 101, 0.16), transparent 22rem),
			linear-gradient(135deg, #efe3c2, #d8c89f 46%, #efe8d6);
		color: #1f241c;
		padding: clamp(1rem, 3vw, 3rem);
	}

	.orion-zoo__header {
		margin: 0 auto 1.4rem;
		max-width: 78rem;
		border: 1px solid rgba(87, 55, 24, 0.24);
		border-radius: 2rem;
		background: rgba(255, 250, 231, 0.72);
		padding: clamp(1.1rem, 3vw, 2.2rem);
		box-shadow: 0 1.5rem 4rem rgba(55, 38, 16, 0.15);
	}

	.orion-zoo__header p,
	.orion-zoo__copy p {
		margin: 0 0 0.35rem;
		color: #8b2f23;
		font-family: var(--font-serif);
		font-size: 0.76rem;
		font-weight: 850;
		letter-spacing: 0.22em;
		text-transform: uppercase;
	}

	.orion-zoo__header h1 {
		margin: 0;
		font-family: var(--font-serif);
		font-size: clamp(2.4rem, 7vw, 6.4rem);
		font-weight: 950;
		letter-spacing: -0.06em;
		line-height: 0.9;
	}

	.orion-zoo__header span,
	.orion-zoo__copy span {
		display: block;
		max-width: 58ch;
		color: rgba(31, 36, 28, 0.68);
		font-family: var(--font-reader);
		font-size: 1rem;
		line-height: 1.55;
	}

	.orion-zoo__grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: clamp(0.9rem, 2vw, 1.4rem);
		margin: 0 auto;
		max-width: 78rem;
	}

	.orion-zoo__principles {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: clamp(0.7rem, 1.6vw, 1rem);
		margin: 0 auto 1.4rem;
		max-width: 78rem;
	}

	.orion-zoo__principles article {
		border: 1px solid rgba(87, 55, 24, 0.2);
		border-left: 0.22rem solid #8b2f23;
		border-radius: 1.1rem;
		background: rgba(255, 250, 231, 0.62);
		padding: 0.8rem 0.9rem;
	}

	.orion-zoo__principles strong {
		display: block;
		margin-bottom: 0.24rem;
		color: #1f241c;
		font-family: var(--font-serif);
		font-size: 0.86rem;
		font-weight: 900;
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}

	.orion-zoo__principles span {
		display: block;
		color: rgba(31, 36, 28, 0.66);
		font-family: var(--font-reader);
		font-size: 0.84rem;
		line-height: 1.45;
	}

	.orion-zoo__card {
		display: grid;
		gap: 1rem;
		border: 1px solid rgba(87, 55, 24, 0.22);
		border-radius: 1.75rem;
		background:
			linear-gradient(90deg, rgba(126, 42, 32, 0.08) 1px, transparent 1px),
			linear-gradient(rgba(126, 42, 32, 0.05) 1px, transparent 1px),
			rgba(255, 251, 235, 0.76);
		background-size: 2rem 2rem;
		padding: 1rem;
		box-shadow: 0 1rem 3rem rgba(55, 38, 16, 0.12);
	}

	.orion-zoo__stage {
		display: grid;
		min-height: 15rem;
		overflow: hidden;
		place-items: center;
		border: 1px solid rgba(87, 55, 24, 0.16);
		border-radius: 1.35rem;
		background:
			radial-gradient(circle at 50% 45%, rgba(183, 131, 47, 0.17), transparent 9rem),
			rgba(239, 226, 194, 0.58);
	}

	.orion-zoo__sizes {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0.6rem;
	}

	.orion-zoo__sizes div {
		display: grid;
		grid-template-rows: 1fr auto;
		min-height: 8.8rem;
		overflow: hidden;
		place-items: center;
		border: 1px solid rgba(87, 55, 24, 0.14);
		border-radius: 1rem;
		background: rgba(255, 250, 231, 0.56);
		padding: 0.5rem;
	}

	.orion-zoo__sizes span {
		color: rgba(31, 36, 28, 0.54);
		font-family: var(--font-serif);
		font-size: 0.68rem;
		font-variant-caps: small-caps;
		font-weight: 800;
		letter-spacing: 0.1em;
	}

	.orion-zoo__sizes :global(.orion-illuminated-sprite) {
		max-width: 90%;
		max-height: 6.4rem;
	}

	@media (max-width: 64rem) {
		.orion-zoo__grid,
		.orion-zoo__principles {
			grid-template-columns: 1fr;
		}
	}
</style>
