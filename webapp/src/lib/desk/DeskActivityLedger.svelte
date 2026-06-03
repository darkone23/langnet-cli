<script lang="ts">
	import { Activity, Clock3 } from 'lucide-svelte';
	import type { DeskActivityItem } from '$lib/desk/desk-activity';

	type Props = {
		items: DeskActivityItem[];
	};

	let { items }: Props = $props();
</script>

{#if items.length}
	<section class="orion-activity-ledger" aria-busy="true" aria-live="polite">
		<header>
			<div>
				<Activity size={16} />
				<span>Desk activity</span>
			</div>
			<strong>{items.length === 1 ? '1 active wait' : `${items.length} active waits`}</strong>
		</header>

		<div class="orion-activity-list">
			{#each items as item}
				<div class="orion-activity-row">
					<span class="orion-activity-dot" aria-hidden="true"></span>
					<div class="orion-activity-text">
						<span>{item.label}</span>
						<small>{item.detail}</small>
					</div>
					<span class="orion-activity-time">
						<Clock3 size={13} />
						{item.elapsedSeconds}s
					</span>
				</div>
			{/each}
		</div>
	</section>
{/if}

<style>
	.orion-activity-ledger {
		border: 1px solid color-mix(in oklab, var(--color-accent) 24%, var(--color-base-300));
		border-left: 0.2rem solid color-mix(in oklab, var(--color-secondary) 62%, var(--color-accent));
		border-radius: var(--radius-box);
		background: color-mix(in oklab, var(--color-base-100) 90%, var(--color-secondary) 5%);
		box-shadow: 0 0.6rem 1.5rem color-mix(in oklab, var(--color-base-content) 6%, transparent);
		padding: 0.7rem;
	}

	.orion-activity-ledger header,
	.orion-activity-ledger header div,
	.orion-activity-row,
	.orion-activity-time {
		display: flex;
		align-items: center;
	}

	.orion-activity-ledger header {
		justify-content: space-between;
		gap: 0.75rem;
		color: color-mix(in oklab, var(--color-base-content) 68%, transparent);
		font-size: 0.75rem;
		font-weight: 800;
		text-transform: uppercase;
	}

	.orion-activity-ledger header div {
		gap: 0.4rem;
	}

	.orion-activity-ledger header strong {
		color: color-mix(in oklab, var(--color-base-content) 58%, var(--color-secondary));
		font-size: 0.68rem;
		text-transform: none;
	}

	.orion-activity-list {
		display: grid;
		gap: 0.45rem;
		margin-top: 0.65rem;
	}

	.orion-activity-row {
		gap: 0.55rem;
		min-width: 0;
		border-radius: calc(var(--radius-box) - 0.15rem);
		background: color-mix(in oklab, var(--color-base-200) 54%, transparent);
		padding: 0.48rem 0.55rem;
	}

	.orion-activity-dot {
		width: 0.55rem;
		height: 0.55rem;
		flex: 0 0 auto;
		border-radius: 999px;
		background: var(--color-secondary);
		box-shadow: 0 0 0 0.28rem color-mix(in oklab, var(--color-secondary) 14%, transparent);
		animation: orion-activity-dot 1.3s ease-in-out infinite;
	}

	.orion-activity-text {
		min-width: 0;
		flex: 1 1 auto;
	}

	.orion-activity-text span,
	.orion-activity-text small {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.orion-activity-text span {
		font-family: var(--font-serif);
		font-size: 0.88rem;
		font-weight: 800;
	}

	.orion-activity-text small {
		color: color-mix(in oklab, var(--color-base-content) 55%, transparent);
		font-size: 0.72rem;
	}

	.orion-activity-time {
		flex: 0 0 auto;
		gap: 0.25rem;
		border: 1px solid color-mix(in oklab, var(--color-base-content) 9%, transparent);
		border-radius: 999px;
		background: color-mix(in oklab, var(--color-base-100) 82%, transparent);
		padding: 0.18rem 0.45rem;
		color: color-mix(in oklab, var(--color-base-content) 62%, var(--color-secondary));
		font-size: 0.72rem;
		font-variant-numeric: tabular-nums;
		font-weight: 800;
	}

	@keyframes orion-activity-dot {
		0%,
		100% {
			opacity: 0.55;
			transform: scale(0.88);
		}

		50% {
			opacity: 1;
			transform: scale(1.12);
		}
	}
</style>
