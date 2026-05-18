<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount, tick } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import { bootStateStorageKey, shouldFastBoot } from '$lib/boot-state';
	import { installReloadDiagnostics } from '$lib/reload-diagnostics';
	import { uiCopy } from '$lib/ui-copy';
	import '../app.css';

	let { children } = $props();
	let booting = $state(true);

	onMount(() => {
		const removeReloadDiagnostics = installReloadDiagnostics();
		void revealWhenStable();

		return () => {
			removeReloadDiagnostics();
		};
	});

	async function revealWhenStable() {
		document.documentElement.classList.add('orion-booting');
		syncDocumentTheme();

		if (shouldSkipBootGate()) {
			booting = false;
			document.documentElement.classList.remove('orion-booting');
			return;
		}

		await tick();
		await waitForFonts();
		await nextFrame();
		await nextFrame();

		booting = false;
		markBootReady();
		document.documentElement.classList.remove('orion-booting');
	}

	function shouldSkipBootGate() {
		if (!browser) return false;
		try {
			return shouldFastBoot(sessionStorage.getItem(bootStateStorageKey));
		} catch {
			return false;
		}
	}

	function markBootReady() {
		if (!browser) return;
		try {
			sessionStorage.setItem(bootStateStorageKey, String(Date.now()));
		} catch {
			// Boot gating must not depend on storage availability.
		}
	}

	function syncDocumentTheme() {
		if (!browser) return;

		try {
			const theme = localStorage.getItem('orion-theme');
			document.documentElement.dataset.theme =
				theme === 'vespers' || theme === 'manuscript' ? theme : 'manuscript';
		} catch {
			document.documentElement.dataset.theme = 'manuscript';
		}
	}

	async function waitForFonts() {
		if (!('fonts' in document)) return;

		const readerSample = 'aṣṭāṅga aṅga puruṣa λόγος νύξ nox nexus';
		const devanagariSample = 'धर्म पुरुष पुराण';
		const fontLoads = [
			document.fonts.load('400 1rem "Noto Serif"', readerSample),
			document.fonts.load('400 italic 1rem "Noto Serif"', readerSample),
			document.fonts.load('600 1rem "Noto Serif"', readerSample),
			document.fonts.load('700 1rem "Noto Serif"', readerSample),
			document.fonts.load('400 1rem "Noto Serif Devanagari"', devanagariSample),
			document.fonts.load('600 1rem "Noto Serif Devanagari"', devanagariSample),
			document.fonts.load('700 1rem "Noto Serif Devanagari"', devanagariSample),
			document.fonts.ready
		];

		await Promise.race([
			Promise.allSettled(fontLoads).catch(() => undefined),
			new Promise((resolve) => setTimeout(resolve, 2600))
		]);
	}

	function nextFrame() {
		return new Promise((resolve) => requestAnimationFrame(() => resolve(undefined)));
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class:orion-app-hidden={booting} aria-hidden={booting}>
	{@render children()}
</div>

{#if booting}
	<div class="orion-global-loader" role="status" aria-live="polite" aria-label={uiCopy.boot.aria}>
		<div class="orion-font-probe" aria-hidden="true">
			<span>Project Orion aṣṭāṅga aṅga puruṣa λόγος νύξ nox nexus</span>
			<strong>धर्म पुरुष पुराण</strong>
			<em>aṣṭāṅga λόγος</em>
		</div>
		<div class="orion-global-loader-mark" aria-hidden="true">
			<span></span>
			<span></span>
			<span></span>
		</div>
		<div class="orion-global-loader-copy">
			<div>{uiCopy.boot.title}</div>
			<p>{uiCopy.boot.detail}</p>
		</div>
	</div>
{/if}
