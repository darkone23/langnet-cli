import assert from 'node:assert/strict';
import { bootStateTtlMs, shouldFastBoot } from './boot-state';

const now = 1_000_000;

assert.equal(shouldFastBoot(null, now), false);
assert.equal(shouldFastBoot('', now), false);
assert.equal(shouldFastBoot('not-a-number', now), false);
assert.equal(shouldFastBoot(String(now - 1_000), now), true);
assert.equal(shouldFastBoot(String(now - bootStateTtlMs - 1), now), false);
