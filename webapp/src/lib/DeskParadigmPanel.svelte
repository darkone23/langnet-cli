<script lang="ts">
	import { ScrollText } from 'lucide-svelte';
	import {
		learnerDisplayForm,
		paradigmSlotGroups,
		paradigmSlotMatchesCandidate
	} from '$lib/paradigm-ui';
	import type { ParadigmPayload } from '$lib/paradigm';
	import type { ParadigmResolutionCandidate } from '$lib/paradigm-resolution';
	import type { LanguageMode } from '$lib/search-data';
	import {
		candidateLearningLanguage,
		learningConcepts,
		learningFosterBridges,
		learningGatewayTitle,
		learningNativeGateways,
		learningPrimarySummary,
		paradigmCandidateKey,
		paradigmCandidateSubtitle,
		paradigmCandidateTitle,
		paradigmFeatureEntries,
		paradigmFunctionalLabels,
		paradigmRelationLabel,
		paradigmSlotFeatureSummary,
		paradigmTableAxisNotes,
		paradigmTableLearningSummary,
		paradigmTableLearningTitle
	} from '$lib/desk-paradigm';

	type Props = {
		candidates: ParadigmResolutionCandidate[];
		hiddenCount: number;
		payloads: Record<string, ParadigmPayload>;
		loading: Record<string, boolean>;
		errors: Record<string, string>;
		searchedForm: string | null | undefined;
		normalizedForm: string | null | undefined;
		fallbackQuery: string;
		fallbackLanguage: LanguageMode;
		onLoadParadigm: (candidate: ParadigmResolutionCandidate) => void;
	};

	let {
		candidates,
		hiddenCount,
		payloads,
		loading,
		errors,
		searchedForm,
		normalizedForm,
		fallbackQuery,
		fallbackLanguage,
		onLoadParadigm
	}: Props = $props();

	let displaySearchedForm = $derived(learnerDisplayForm(searchedForm));
	let displayNormalizedForm = $derived(learnerDisplayForm(normalizedForm));

	function countLabel(count: number, singular: string, plural = `${singular}s`) {
		return `${count} ${count === 1 ? singular : plural}`;
	}
</script>

{#if candidates.length}
	<section class="orion-paradigm-panel orion-manuscript-panel">
		<header class="orion-paradigm-head">
			<div>
				<h3>
					<ScrollText size={18} />
					Forms
				</h3>
				<p>
					{displaySearchedForm}
					{#if displayNormalizedForm && displayNormalizedForm !== displaySearchedForm}
						<span>· {displayNormalizedForm}</span>
					{/if}
				</p>
			</div>
			<span>{countLabel(candidates.length, 'reading')}</span>
		</header>

		<div class="orion-paradigm-candidates">
			{#each candidates as candidate}
				{@const candidateKey = paradigmCandidateKey(candidate)}
				{@const features = paradigmFeatureEntries(candidate)}
				{@const relations = paradigmFunctionalLabels(candidate)}
				{@const learning = learningConcepts(candidate)}
				{@const nativeGateways = learningNativeGateways(
					learning,
					candidateLearningLanguage(candidate, fallbackLanguage)
				)}
				{@const fosterBridges = learningFosterBridges(learning)}
				{@const paradigm = payloads[candidateKey]}
				<article class="orion-paradigm-card">
					<div class="orion-paradigm-card-head">
						<div>
							<h4>{paradigmCandidateTitle(candidate, fallbackQuery)}</h4>
							{#if paradigmCandidateSubtitle(candidate)}
								<p>{paradigmCandidateSubtitle(candidate)}</p>
							{/if}
						</div>
						{#if candidate.paradigm_request}
							<button
								type="button"
								class="orion-paradigm-load"
								disabled={Boolean(loading[candidateKey] || paradigm)}
								onclick={() => onLoadParadigm(candidate)}
							>
								{#if loading[candidateKey]}
									<span class="loading loading-spinner loading-xs"></span>
								{/if}
								{paradigm ? 'Table loaded' : 'Load table'}
							</button>
						{:else if candidate.unresolved_reason}
							<span class="orion-paradigm-unresolved">
								{paradigmRelationLabel(candidate.unresolved_reason)}
							</span>
						{/if}
					</div>

					{#if features.length || relations.length}
						<div class="orion-paradigm-tags">
							{#each features as feature}
								<span><b>{feature.key}</b>{feature.value}</span>
							{/each}
							{#each relations as relation}
								<span class="orion-paradigm-relation">{relation}</span>
							{/each}
						</div>
					{/if}

					{#if learning.length}
						<section class="orion-learning-strip">
							<div class="orion-learning-head">
								<span>Learn this form</span>
								<strong>{learningGatewayTitle(learning)}</strong>
							</div>
							{#if learningPrimarySummary(candidate)}
								<p>{learningPrimarySummary(candidate)}</p>
							{/if}
							{#if nativeGateways.length}
								<div class="orion-learning-chips">
									{#each nativeGateways as gateway}
										<span title={gateway.explanation}>
											<b>{gateway.label}</b>
											{gateway.term}
											{#if gateway.role}<em>{gateway.role}</em>{/if}
										</span>
									{/each}
								</div>
							{/if}
							{#if fosterBridges.length}
								<div class="orion-learning-bridges">
									{#each fosterBridges as bridge}
										<span
											class={bridge.status === 'aggregate_candidate'
												? 'orion-learning-bridge orion-learning-bridge-related'
												: 'orion-learning-bridge'}
										>
											<b>Try this</b>
											{bridge.learner_action || bridge.plain_english}
										</span>
									{/each}
								</div>
							{/if}
							<a class="orion-learning-open" href="/learn">Open the learning path</a>
						</section>
					{/if}

					{#if errors[candidateKey]}
						<div class="orion-paradigm-warning">{errors[candidateKey]}</div>
					{/if}

					{#if paradigm}
						<div class="orion-paradigm-tables">
							{#each paradigm.paradigms as block}
								{@const slotGroups = paradigmSlotGroups(block)}
								{@const axisNotes = paradigmTableAxisNotes(block)}
								<section class="orion-paradigm-table">
									<div class="orion-paradigm-table-head">
										<span>{block.label}</span>
										<small>{block.dimensions.join(' · ')}</small>
									</div>
									<section class="orion-table-learning">
										<div class="orion-table-learning-head">
											<span>{paradigmTableLearningTitle(candidate)}</span>
											<p>{paradigmTableLearningSummary(candidate, block)}</p>
										</div>
										{#if axisNotes.length}
											<div class="orion-table-axis-notes">
												{#each axisNotes as axis}
													<span><b>{axis.label}</b>{axis.note}</span>
												{/each}
											</div>
										{/if}
									</section>
									<div class="orion-paradigm-slot-groups">
										{#each slotGroups as group}
											<section class="orion-paradigm-slot-group">
												<h5>{group.label}</h5>
												<div class="orion-paradigm-slots">
													{#each group.slots as slot}
														<div
															class={paradigmSlotMatchesCandidate(slot, candidate, fallbackQuery)
																? 'orion-paradigm-slot orion-paradigm-slot-match'
																: 'orion-paradigm-slot'}
														>
															<span class="orion-paradigm-slot-feature">
																{paradigmSlotFeatureSummary(slot.features)}
															</span>
															<span class="orion-paradigm-slot-forms">
																{slot.forms.map((form) => form.text).join(', ')}
															</span>
														</div>
													{/each}
												</div>
											</section>
										{/each}
									</div>
								</section>
							{/each}
						</div>
					{/if}
				</article>
			{/each}
			{#if hiddenCount}
				<p class="orion-paradigm-hidden-note">
					{countLabel(hiddenCount, 'additional reading')} held back from the first view.
				</p>
			{/if}
		</div>
	</section>
{/if}

<style>
	.orion-paradigm-panel,
	.orion-paradigm-candidates,
	.orion-paradigm-card,
	.orion-learning-strip,
	.orion-table-learning,
	.orion-paradigm-tables,
	.orion-paradigm-table,
	.orion-paradigm-slot-groups,
	.orion-paradigm-slot-group,
	.orion-paradigm-slot {
		display: grid;
	}

	.orion-paradigm-head,
	.orion-paradigm-card-head,
	.orion-paradigm-tags,
	.orion-learning-chips,
	.orion-learning-bridges,
	.orion-table-axis-notes,
	.orion-paradigm-table-head {
		display: flex;
		flex-wrap: wrap;
		gap: 0.55rem;
	}

	.orion-paradigm-head,
	.orion-paradigm-card-head,
	.orion-paradigm-table-head {
		align-items: start;
		justify-content: space-between;
	}

	.orion-paradigm-head {
		border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
	}

	.orion-paradigm-head h3 {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 84%, var(--color-primary));
		font-family: var(--font-serif);
		font-size: 1.4rem;
		font-weight: 700;
		line-height: 1.15;
	}

	.orion-paradigm-head p,
	.orion-paradigm-head > span,
	.orion-paradigm-hidden-note {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 58%, transparent);
		font-family: var(--font-serif);
		font-size: 0.82rem;
		font-variant-caps: small-caps;
		font-weight: 650;
		line-height: 1.35;
	}

	.orion-paradigm-card {
		gap: 0.62rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
		border-left: 0.2rem solid color-mix(in oklab, var(--color-primary) 48%, var(--color-accent));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-base-200));
	}

	.orion-paradigm-card h4 {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-secondary));
		font-family: var(--font-serif);
		font-weight: 700;
		line-height: 1.2;
	}

	.orion-paradigm-card p,
	.orion-learning-strip p,
	.orion-table-learning-head p {
		margin: 0.18rem 0 0;
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		line-height: 1.35;
	}

	.orion-paradigm-load,
	.orion-paradigm-unresolved,
	.orion-paradigm-tags span,
	.orion-learning-chips span,
	.orion-learning-bridge,
	.orion-table-axis-notes span {
		display: inline-flex;
		align-items: baseline;
		gap: 0.25rem;
		max-width: 100%;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-base-200));
		padding: 0.18rem 0.48rem;
		color: color-mix(in oklab, var(--color-base-content) 66%, transparent);
		font-size: 0.72rem;
		line-height: 1.25;
	}

	.orion-paradigm-load {
		align-items: center;
		border-color: color-mix(in oklab, var(--color-secondary) 28%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 88%, var(--color-secondary) 6%);
		cursor: pointer;
		font-weight: 700;
	}

	.orion-paradigm-unresolved,
	.orion-paradigm-warning {
		border-color: color-mix(in oklab, var(--color-warning) 28%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-warning) 7%);
		color: color-mix(in oklab, var(--color-base-content) 68%, var(--color-warning));
	}

	.orion-paradigm-tags b,
	.orion-learning-chips b,
	.orion-learning-bridge b,
	.orion-table-axis-notes b {
		flex: 0 0 auto;
		color: color-mix(in oklab, var(--color-base-content) 48%, transparent);
		font-family: var(--font-serif);
		font-variant-caps: small-caps;
		font-weight: 750;
	}

	.orion-paradigm-tags .orion-paradigm-relation {
		background: color-mix(in oklab, var(--color-base-100) 86%, var(--color-primary) 6%);
		color: color-mix(in oklab, var(--color-base-content) 68%, var(--color-primary));
	}

	.orion-learning-strip {
		gap: 0.42rem;
		border-left: 0.18rem solid color-mix(in oklab, var(--color-accent) 42%, var(--color-base-300));
		padding: 0.2rem 0 0.2rem 0.62rem;
	}

	.orion-learning-head,
	.orion-table-learning-head {
		display: grid;
		gap: 0.16rem;
	}

	.orion-learning-head span,
	.orion-paradigm-slot-group h5,
	.orion-paradigm-table-head small {
		color: color-mix(in oklab, var(--color-base-content) 46%, transparent);
		font-family: var(--font-serif);
		font-size: 0.68rem;
		font-variant-caps: small-caps;
		font-weight: 750;
		line-height: 1.2;
	}

	.orion-learning-head strong,
	.orion-table-learning-head span {
		overflow-wrap: anywhere;
		color: color-mix(in oklab, var(--color-base-content) 76%, var(--color-accent));
		font-family: var(--font-serif);
		font-weight: 750;
		line-height: 1.25;
	}

	.orion-learning-chips em {
		color: color-mix(in oklab, var(--color-base-content) 48%, var(--color-accent));
		font-style: normal;
	}

	.orion-learning-bridge {
		border-radius: 0.3rem;
		overflow-wrap: anywhere;
	}

	.orion-learning-bridge-related {
		border-color: color-mix(in oklab, var(--color-warning) 24%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-warning) 6%);
	}

	.orion-paradigm-warning,
	.orion-paradigm-hidden-note {
		color: color-mix(in oklab, var(--color-base-content) 52%, transparent);
		font-size: 0.72rem;
		line-height: 1.35;
	}

	.orion-paradigm-hidden-note {
		border-top: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		padding-top: 0.35rem;
	}

	.orion-paradigm-warning,
	.orion-table-learning,
	.orion-paradigm-slot {
		border-radius: var(--radius-box);
	}

	.orion-paradigm-table,
	.orion-table-learning {
		gap: 0.45rem;
	}

	.orion-paradigm-table-head {
		align-items: baseline;
		color: color-mix(in oklab, var(--color-base-content) 66%, transparent);
		font-family: var(--font-serif);
		font-weight: 700;
	}

	.orion-table-learning {
		border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		background: color-mix(in oklab, var(--color-base-100) 92%, var(--color-secondary) 4%);
	}

	.orion-paradigm-slot-groups {
		gap: 0.58rem;
	}

	.orion-paradigm-slot-group {
		gap: 0.32rem;
	}

	.orion-paradigm-slot-group h5 {
		margin: 0;
		color: color-mix(in oklab, var(--color-base-content) 56%, var(--color-primary));
		font-size: 0.72rem;
	}

	.orion-paradigm-slots {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
		gap: 0.32rem;
	}

	.orion-paradigm-slot {
		gap: 0.16rem;
		min-width: 0;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
		background: color-mix(in oklab, var(--color-base-100) 96%, var(--color-base-200));
	}

	.orion-paradigm-slot-match {
		border-color: color-mix(in oklab, var(--color-primary) 36%, var(--color-base-300));
		background: color-mix(in oklab, var(--color-base-100) 82%, var(--color-primary) 9%);
	}

	.orion-paradigm-slot-feature {
		color: color-mix(in oklab, var(--color-base-content) 50%, transparent);
		font-size: 0.64rem;
		line-height: 1.25;
	}

	.orion-paradigm-slot-forms {
		overflow-wrap: anywhere;
		color: color-mix(in oklab, var(--color-base-content) 82%, var(--color-primary));
		font-family: var(--font-reader);
		font-size: 0.86rem;
		font-weight: 650;
		line-height: 1.3;
	}
</style>
