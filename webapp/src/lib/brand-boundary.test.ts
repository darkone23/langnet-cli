import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const uiCopySource = readFileSync(new URL('./ui-copy.ts', import.meta.url), 'utf8');
const publicRouteSources = [
	'../routes/+page.svelte',
	'../routes/about/+page.svelte',
	'../routes/evidence/+page.svelte',
	'../routes/learn/+page.svelte',
	'../routes/library/+page.svelte',
	'../routes/languages/latin/+page.svelte',
	'../routes/languages/greek/+page.svelte',
	'../routes/languages/sanskrit/+page.svelte'
].map((path) => readFileSync(new URL(path, import.meta.url), 'utf8'));

assert.ok(
	uiCopySource.includes("name: 'Project Orion'"),
	'Public app chrome should use Project Orion as the visible product name'
);

assert.ok(
	uiCopySource.includes("eyebrow: 'Project Orion'"),
	'Public landing copy should lead with Project Orion'
);

assert.equal(
	/\bLangNet\b/.test(uiCopySource),
	false,
	'Public UI copy should not expose the internal LangNet name'
);

for (const source of publicRouteSources) {
	assert.equal(
		/\bLangNet\b/.test(source),
		false,
		'Public Svelte routes should not expose the internal LangNet name'
	);
}
