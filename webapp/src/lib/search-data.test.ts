import assert from 'node:assert/strict';
import { encounterWord, resolveToolRequests, toolsForLanguage } from './search-data';

const latinTools = toolsForLanguage('lat').map(({ id }) => id);
assert.ok(latinTools.includes('lewis_1890'));
assert.deepEqual(resolveToolRequests('lat', ['lewis_1890']), ['lewis_1890']);
assert.ok(encounterWord('', 'lat', ['all']).source_tools.includes('lewis_1890'));

const greekTools = toolsForLanguage('grc').map(({ id }) => id);
assert.ok(greekTools.includes('bailly'));
assert.deepEqual(resolveToolRequests('grc', ['bailly']), ['bailly']);
assert.ok(encounterWord('', 'grc', ['all']).source_tools.includes('bailly'));
