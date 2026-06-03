<script lang="ts">
	import type { HeadwordDisplay } from '$lib/headword-display';

	type Props = {
		display: HeadwordDisplay;
		lead?: string;
		sourceLine?: string;
	};

	let { display, lead = '', sourceLine = '' }: Props = $props();

	let titleClass = $derived(illuminatedTitleClass(display.title));

	function illuminatedTitleClass(title: HeadwordDisplay['title']) {
		const base = 'orion-illuminated-title font-serif text-3xl leading-tight';
		if (!title) return base;
		if (title.script === 'devanagari') {
			return `${base} orion-illuminated-title-explicit orion-illuminated-title-devanagari`;
		}
		return `${base} orion-illuminated-title-explicit`;
	}
</script>

<div class="orion-entry-bookplate">
	<h3
		class={titleClass}
		lang={display.primaryLang}
		aria-label={display.title ? display.primary : undefined}
	>
		{#if display.title?.script === 'devanagari'}
			<span class="orion-devanagari-title" aria-hidden="true">
				<span class="orion-devanagari-initial">
					<span class="orion-devanagari-initial-glyph">
						{display.title.initial}
					</span>
				</span>
				{#if display.title.rest}
					<span class="orion-devanagari-connector"></span>
					<span class="orion-devanagari-rest">{display.title.rest}</span>
				{/if}
			</span>
		{:else if display.title}
			<span class="orion-plain-title" aria-hidden="true">
				<span class="orion-plain-initial">
					<span class="orion-plain-initial-glyph">
						{display.title.initial}
					</span>
				</span>
				{#if display.title.rest}
					<span class="orion-plain-rest">{display.title.rest}</span>
				{/if}
			</span>
		{:else}
			{display.primary}
		{/if}
	</h3>
	{#if display.forms.length}
		<div class="orion-headword-forms" aria-label="Headword forms">
			{#each display.forms as form}
				<span class="orion-headword-form">
					<span class="orion-headword-form-label">{form.label}</span>
					{#if form.kind === 'code'}
						<code>{form.value}</code>
					{:else}
						<span>{form.value}</span>
					{/if}
				</span>
			{/each}
		</div>
	{/if}
	{#if lead}
		<p class="orion-entry-lead">{lead}</p>
	{/if}
</div>

{#if sourceLine}
	<p class="orion-entry-source-line">{sourceLine}</p>
{/if}

<style>
	.orion-entry-bookplate {
		--orion-illuminated-fill: color-mix(in oklab, var(--color-primary) 64%, var(--color-accent));
		--orion-illuminated-fill-left: 0.88rem;
		--orion-illuminated-fill-width: 4.25rem;
		--orion-illuminated-rise-height: 1.02rem;

		position: relative;
		max-width: min(100%, 68ch);
		overflow: visible;
		border: 2px double color-mix(in oklab, var(--color-accent) 34%, var(--color-base-content));
		border-inline-start: 0.24rem solid
			color-mix(in oklab, var(--color-secondary) 42%, var(--color-base-content));
		border-radius: 0.28rem 0.18rem 0.18rem 0.28rem;
		background: color-mix(in oklab, var(--color-base-100) 98%, var(--color-accent) 2%);
		padding: 0.78rem 0.98rem 0.82rem;
		box-shadow:
			inset 0 0 0 1px color-mix(in oklab, var(--color-base-content) 4%, transparent),
			0 0.32rem 0.8rem color-mix(in oklab, var(--color-neutral) 4%, transparent);
	}

	.orion-entry-bookplate::before,
	.orion-entry-bookplate::after {
		display: none;
	}

	.orion-illuminated-title {
		position: relative;
		z-index: 2;
		display: flow-root;
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		font-family: var(--font-reader);
		font-feature-settings:
			'kern' 1,
			'liga' 1;
		font-kerning: normal;
		overflow-wrap: anywhere;
		text-shadow: 0 1px 0 color-mix(in oklab, var(--color-base-100) 88%, transparent);
	}

	.orion-illuminated-title::first-letter {
		float: left;
		margin: 0.04rem 0.5rem 0 0;
		border: 0;
		border-radius: 0.2rem;
		background: var(--orion-illuminated-fill);
		padding: 0 0.28rem 0.42rem;
		color: var(--color-primary-content);
		font-size: 1.75em;
		line-height: 1;
		box-shadow:
			0.07rem 0.08rem 0 color-mix(in oklab, var(--color-secondary) 18%, transparent),
			0 0.18rem 0.45rem color-mix(in oklab, var(--color-neutral) 6%, transparent);
	}

	.orion-illuminated-title-explicit,
	.orion-illuminated-title-devanagari {
		display: block;
		overflow: visible;
		overflow-wrap: normal;
	}

	.orion-illuminated-title-explicit::first-letter,
	.orion-illuminated-title-devanagari::first-letter {
		float: none;
		margin: 0;
		border: 0;
		background: transparent;
		padding: 0;
		color: inherit;
		font-size: inherit;
		line-height: inherit;
		box-shadow: none;
	}

	.orion-plain-title {
		position: relative;
		z-index: 2;
		display: flow-root;
		max-width: 100%;
		color: color-mix(in oklab, var(--color-base-content) 88%, var(--color-primary));
		overflow-wrap: anywhere;
	}

	.orion-plain-initial {
		float: left;
		margin: 0.04rem 0.5rem 0 0;
		border: 0;
		border-radius: 0.2rem;
		background: var(--orion-illuminated-fill);
		padding: 0 0.28rem 0.42rem;
		color: var(--color-primary-content);
		font-size: 1.75em;
		line-height: 1;
		box-shadow:
			0.07rem 0.08rem 0 color-mix(in oklab, var(--color-secondary) 18%, transparent),
			0 0.18rem 0.45rem color-mix(in oklab, var(--color-neutral) 6%, transparent);
	}

	.orion-plain-initial-glyph {
		display: inline-block;
		line-height: 1;
	}

	.orion-plain-rest {
		overflow-wrap: anywhere;
	}

	.orion-devanagari-title {
		--orion-deva-title-y: -0.1em;
		--orion-deva-initial-glyph-y: -0.13em;
		--orion-deva-initial-fill-bleed-block: 0.18em;
		--orion-deva-connector-width: 0.38em;
		--orion-deva-connector-x: -0.07em;
		--orion-deva-connector-y: 0.22em;
		--orion-deva-rest-x: -0.29em;
		--orion-deva-rest-y: -0.02em;

		position: relative;
		z-index: 2;
		display: inline-flex;
		isolation: isolate;
		max-width: 100%;
		align-items: flex-start;
		color: color-mix(in oklab, var(--color-base-content) 86%, var(--color-primary));
		transform: translateY(var(--orion-deva-title-y));
		white-space: nowrap;
	}

	.orion-devanagari-initial {
		position: relative;
		z-index: 2;
		display: inline-grid;
		isolation: isolate;
		overflow: visible;
		place-items: center;
		margin: 0;
		border: 0;
		border-radius: 0.2rem;
		background: var(--orion-illuminated-fill);
		padding: 0 0.28rem 0.42rem;
		color: var(--color-primary-content);
		font-size: 1.75em;
		line-height: 1;
		box-shadow:
			0.07rem 0.08rem 0 color-mix(in oklab, var(--color-secondary) 18%, transparent),
			0 0.18rem 0.45rem color-mix(in oklab, var(--color-neutral) 6%, transparent);
	}

	.orion-devanagari-initial::before {
		position: absolute;
		z-index: -1;
		top: calc(-1 * var(--orion-deva-initial-fill-bleed-block));
		bottom: 0;
		inset-inline: -1px;
		border-radius: inherit;
		background: inherit;
		content: '';
	}

	.orion-devanagari-initial-glyph {
		display: inline-block;
		line-height: 1;
		transform: translateY(var(--orion-deva-initial-glyph-y));
	}

	.orion-devanagari-connector {
		position: relative;
		z-index: 5;
		display: inline-block;
		flex: 0 0 var(--orion-deva-connector-width);
		height: 1em;
		margin-left: -0.04em;
		pointer-events: none;
		transform: translate(var(--orion-deva-connector-x), var(--orion-deva-connector-y));
	}

	.orion-devanagari-connector::before {
		position: absolute;
		z-index: 5;
		top: 0;
		right: -0.18em;
		left: -0.08em;
		height: 0.085em;
		border-radius: 999px;
		background: linear-gradient(
			90deg,
			transparent 0%,
			currentColor 28%,
			currentColor 74%,
			transparent 100%
		);
		content: '';
		opacity: 0.76;
		filter: drop-shadow(0 0.035em 0 color-mix(in oklab, var(--color-base-100) 72%, transparent));
	}

	.orion-devanagari-rest {
		position: relative;
		z-index: 2;
		display: inline-block;
		min-width: 0;
		margin-left: var(--orion-deva-rest-x);
		line-height: 1.05;
		overflow-wrap: anywhere;
		transform: translateY(var(--orion-deva-rest-y));
	}

	.orion-headword-forms {
		position: relative;
		z-index: 1;
		clear: both;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem 0.55rem;
		margin-top: 0.42rem;
		color: color-mix(in oklab, var(--color-base-content) 56%, transparent);
		font-family: var(--font-serif);
		font-kerning: normal;
		font-size: 0.78rem;
		line-height: 1.4;
	}

	.orion-headword-form {
		display: inline-flex;
		min-width: 0;
		align-items: baseline;
		gap: 0.28rem;
	}

	.orion-headword-form-label {
		color: color-mix(in oklab, var(--color-base-content) 42%, transparent);
		font-size: 0.68rem;
		font-variant-caps: small-caps;
		font-weight: 600;
		letter-spacing: 0;
	}

	.orion-headword-form code {
		min-width: 0;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		border-radius: 0.24rem;
		background: color-mix(in oklab, var(--color-base-200) 62%, transparent);
		padding: 0.02rem 0.28rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
		font-size: 0.72rem;
		overflow-wrap: anywhere;
	}

	.orion-entry-lead {
		position: relative;
		z-index: 1;
		clear: both;
		margin: 0.45rem 0 0;
		max-width: 62ch;
		border-top: 1px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
		border-radius: 0 0 0.16rem 0.16rem;
		background: color-mix(in oklab, var(--color-base-100) 99%, var(--color-accent) 1%);
		padding: 0.5rem 0.7rem 0.05rem;
		color: color-mix(in oklab, var(--color-base-content) 64%, transparent);
		font-family: var(--font-reader);
		font-kerning: normal;
		font-size: 0.98rem;
		line-height: 1.65;
		text-indent: 0;
		text-wrap: pretty;
	}

	.orion-entry-lead::before {
		display: none;
	}

	.orion-entry-source-line {
		margin: 0.5rem 0 0 0.3rem;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-size: 0.85rem;
		line-height: 1.4;
	}

	.orion-entry-source-line::before {
		display: inline-block;
		width: 1.5rem;
		margin-right: 0.45rem;
		border-top: 1px solid color-mix(in oklab, var(--color-accent) 28%, transparent);
		content: '';
		vertical-align: middle;
	}
</style>
