import assert from 'node:assert/strict';
import path from 'node:path';
import { buildCliEnvironment, resolveCliDirectory } from './langnet-cli';

const env = buildCliEnvironment({
	HOME: '/home/learner',
	PATH: '/usr/bin:/bin'
});

assert.equal(env.NO_COLOR, '1');
assert.match(env.PATH ?? '', /(^|:)\/home\/learner\/\.local\/bin(:|$)/);
assert.match(env.PATH ?? '', /(^|:)\/usr\/bin(:|$)/);

const duplicateEnv = buildCliEnvironment({
	HOME: '/home/learner',
	PATH: '/home/learner/.local/bin:/usr/bin'
});

assert.equal(
	duplicateEnv.PATH?.split(':').filter((entry) => entry === '/home/learner/.local/bin').length,
	1
);

assert.equal(
	resolveCliDirectory('/workspace/langnet-cli/webapp', {}),
	path.resolve('/workspace/langnet-cli')
);

assert.equal(
	resolveCliDirectory('/workspace/langnet-cli/webapp', {
		LANGNET_CLI_DIR: '/opt/langnet-cli'
	}),
	'/opt/langnet-cli'
);
