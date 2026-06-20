import { strict as assert } from 'node:assert';
import { createReaderSelectedWordController } from './reader-selected-word-controller';

const state: Record<string, any> = {
	language: 'lat',
	catalogId: 'development',
	selectedWord: '',
	selectedWordBriefing: { old: true },
	selectedWordBriefingLoading: false,
	selectedWordBriefingGenerating: true,
	selectedWordBriefingError: 'old briefing error',
	selectedWordContext: { old: true },
	selectedWordContextLoading: false,
	selectedWordContextError: 'old context error',
	selectedSegment: { work_id: 'work:1', citation_path: '1.1' },
	selectedWork: null
};

const urlUpdates: unknown[] = [];
const briefingCalls: unknown[] = [];
const contextCalls: unknown[] = [];

const controller = createReaderSelectedWordController(state, {
	updateReaderUrl: (overrides) => {
		urlUpdates.push(overrides);
	},
	currentWorkRef: () => 'work:1',
	fetchEncounterBriefing: async (input) => {
		briefingCalls.push(input);
		return {
			response: { ok: true },
			data: { generated: Boolean(input.generate), token: input.token }
		};
	},
	fetchWordContext: async (input) => {
		contextCalls.push(input);
		return {
			response: { ok: true },
			data: { token: input.query, work: input.work, segment: input.segment }
		};
	}
});

await controller.selectToken('“arma,”');

assert.equal(state.selectedWord, 'arma');
assert.deepEqual(urlUpdates.at(-1), { selectedWord: 'arma' });
assert.equal(briefingCalls.length, 1);
assert.equal(contextCalls.length, 1);
assert.deepEqual(state.selectedWordBriefing, { generated: false, token: 'arma' });
assert.deepEqual(state.selectedWordContext, {
	token: 'arma',
	work: 'work:1',
	segment: '1.1'
});
assert.equal(state.selectedWordBriefingLoading, false);
assert.equal(state.selectedWordContextLoading, false);

await controller.fetchEncounterBriefing('arma', true);
assert.deepEqual(state.selectedWordBriefing, { generated: true, token: 'arma' });

controller.reset({ clearWord: true });
assert.equal(state.selectedWord, '');
assert.equal(state.selectedWordBriefing, null);
assert.equal(state.selectedWordContext, null);
assert.equal(state.selectedWordBriefingLoading, false);
assert.equal(state.selectedWordContextLoading, false);

console.log('reader selected-word controller checks complete');
