import { strict as assert } from 'node:assert';
import config from '../../vite.config';

assert.ok(typeof config !== 'function', 'vite config should remain an object config');

const allowedHosts = config.server?.allowedHosts;
const previewAllowedHosts = config.preview?.allowedHosts;

assert.deepEqual(allowedHosts, ['langnet.computerdream.club', 'project-orion.net']);
assert.deepEqual(previewAllowedHosts, allowedHosts);

console.log('vite config ok');
