import assert from 'node:assert/strict';
import { diagnoseReloadCause } from './reload-diagnostics';

assert.equal(
	diagnoseReloadCause({ wasDiscarded: true, navigationType: 'reload' }),
	'browser-discard'
);
assert.equal(
	diagnoseReloadCause({ wasDiscarded: false, navigationType: 'back_forward', persisted: true }),
	'bfcache-restore'
);
assert.equal(
	diagnoseReloadCause({ wasDiscarded: false, navigationType: 'reload' }),
	'document-reload'
);
assert.equal(
	diagnoseReloadCause({ wasDiscarded: false, navigationType: 'navigate' }),
	'document-navigation'
);
assert.equal(
	diagnoseReloadCause({ wasDiscarded: false, navigationType: 'back_forward' }),
	'app-resume'
);
