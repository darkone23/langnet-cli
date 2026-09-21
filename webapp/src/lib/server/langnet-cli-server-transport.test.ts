import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { runJsonCommand, resolveLangnetServerUrl } from './langnet-cli';

type HttpServer = http.Server & { port: number };

function startServer(handler: (req: http.IncomingMessage, res: http.ServerResponse) => void) {
	return new Promise<HttpServer>((resolve) => {
		const server = http.createServer(handler);
		server.listen(0, '127.0.0.1', () => {
			server.port = (server.address() as AddressInfo).port;
			resolve(server as HttpServer);
		});
	});
}

async function closedPort(): Promise<number> {
	const server = await startServer(() => undefined);
	await new Promise<void>((resolve) => server.close(() => resolve()));
	return server.port;
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'langnet-transport-'));
const fakeBinDir = path.join(tmpDir, 'bin');
const spawnMarker = path.join(tmpDir, 'subprocess.marker');
fs.mkdirSync(fakeBinDir);
fs.writeFileSync(
	path.join(fakeBinDir, 'just'),
	`#!/bin/sh\nprintf x >> '${spawnMarker}'\necho '{"source":"subprocess"}'\n`,
	{ mode: 0o755 }
);

const savedEnv = {
	PATH: process.env.PATH,
	LANGNET_CLI_DIR: process.env.LANGNET_CLI_DIR,
	LANGNET_SERVER_URL: process.env.LANGNET_SERVER_URL
};
process.env.PATH = `${fakeBinDir}${path.delimiter}${process.env.PATH ?? ''}`;
process.env.LANGNET_CLI_DIR = tmpDir;

async function resetMarker() {
	await fs.promises.rm(spawnMarker, { force: true });
}

function markerExists() {
	return fs.existsSync(spawnMarker);
}

async function main() {
	// resolveLangnetServerUrl trims trailing slashes and treats blank as unset.
	process.env.LANGNET_SERVER_URL = '  ';
	assert.equal(resolveLangnetServerUrl(), undefined);
	process.env.LANGNET_SERVER_URL = 'http://127.0.0.1:8000/';
	assert.equal(resolveLangnetServerUrl(), 'http://127.0.0.1:8000');
	process.env.LANGNET_SERVER_URL = undefined;
	assert.equal(resolveLangnetServerUrl(), undefined);

	// 1. Flag unset: subprocess exactly as today.
	delete process.env.LANGNET_SERVER_URL;
	await resetMarker();
	const subprocessPayload = await runJsonCommand(['cli', 'langs', '--output', 'json'], 10_000);
	assert.equal(subprocessPayload.source, 'subprocess');
	assert.ok(markerExists(), 'flag unset must use the subprocess transport');

	// 2. Flag set + healthy server: HTTP transport used, subprocess not invoked.
	const healthy = await startServer((req, res) => {
		let body = '';
		req.on('data', (chunk) => {
			body += chunk;
		});
		req.on('end', () => {
			const parsed = JSON.parse(body) as { args?: string[]; stdin?: string | null };
			assert.deepEqual(parsed.args, ['cli', 'langs', '--output', 'json']);
			assert.equal(parsed.stdin, null);
			assert.equal(typeof parsed.timeoutMs, 'number');
			res.writeHead(200, { 'content-type': 'application/json' });
			res.end('{"source":"http"}');
		});
	});
	try {
		process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${healthy.port}`;
		await resetMarker();
		const httpPayload = await runJsonCommand(['cli', 'langs', '--output', 'json'], 10_000, {
			queued: false
		});
		assert.equal(httpPayload.source, 'http');
		assert.ok(!markerExists(), 'server transport must not spawn the CLI');

		// 2b. stdin passthrough reaches the server body.
		let seenStdin: unknown = null;
		const echo = await startServer((req, res) => {
			let body = '';
			req.on('data', (chunk) => {
				body += chunk;
			});
			req.on('end', () => {
				seenStdin = (JSON.parse(body) as { stdin?: unknown }).stdin;
				res.writeHead(200, { 'content-type': 'application/json' });
				res.end('{"source":"http"}');
			});
		});
		try {
			process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${echo.port}`;
			await runJsonCommand(['cli', 'encounter-briefing', '--cache-only'], 10_000, {
				queued: true,
				stdin: '{"query":"arma"}'
			});
			assert.equal(seenStdin, '{"query":"arma"}');
		} finally {
			echo.close();
		}
	} finally {
		healthy.close();
	}

	// 3. Server 500: fall back to subprocess.
	const failing = await startServer((req, res) => {
		res.writeHead(500, { 'content-type': 'application/json' });
		res.end('{"error":"cli exploded"}');
	});
	try {
		process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${failing.port}`;
		await resetMarker();
		const payload = await runJsonCommand(['cli', 'langs', '--output', 'json'], 10_000, {
			queued: false
		});
		assert.equal(payload.source, 'subprocess');
		assert.ok(markerExists(), 'non-200 must fall back to subprocess');
	} finally {
		failing.close();
	}

	// 4. Connection refused: fall back to subprocess.
	const unreachable = await closedPort();
	process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${unreachable}`;
	await resetMarker();
	const refusedPayload = await runJsonCommand(['cli', 'langs', '--output', 'json'], 10_000, {
		queued: false
	});
	assert.equal(refusedPayload.source, 'subprocess');
	assert.ok(markerExists(), 'connection error must fall back to subprocess');

	// 5. Malformed body: fall back to subprocess.
	const malformed = await startServer((req, res) => {
		res.writeHead(200, { 'content-type': 'application/json' });
		res.end('not-json');
	});
	try {
		process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${malformed.port}`;
		await resetMarker();
		const payload = await runJsonCommand(['cli', 'langs', '--output', 'json'], 10_000, {
			queued: false
		});
		assert.equal(payload.source, 'subprocess');
		assert.ok(markerExists(), 'malformed server body must fall back');
	} finally {
		malformed.close();
	}

	// 6. Server timeout: fall back to subprocess within the deadline.
	const hanging = await startServer(() => {
		// Never respond; the client deadline aborts the request.
	});
	try {
		process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${hanging.port}`;
		await resetMarker();
		const started = Date.now();
		const payload = await runJsonCommand(['cli', 'langs', '--output', 'json'], 150, {
			queued: false
		});
		const elapsed = Date.now() - started;
		assert.equal(payload.source, 'subprocess');
		assert.ok(markerExists(), 'server timeout must fall back');
		assert.ok(elapsed < 5_000, `timeout fallback took too long: ${elapsed}ms`);
	} finally {
		hanging.close();
	}

	// 7. Non-allowlisted args: subprocess even when the server flag is set.
	const nosy = await startServer(() => {
		throw new Error('server must not be called for non-allowlisted args');
	});
	try {
		process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${nosy.port}`;
		await resetMarker();
		const payload = await runJsonCommand(['cli', 'databuild', 'reader'], 10_000, {
			queued: false
		});
		assert.equal(payload.source, 'subprocess');
		assert.ok(markerExists(), 'non-allowlisted args must use subprocess');
	} finally {
		nosy.close();
	}

	// 8. Client abort: no subprocess fallback after cancellation.
	const slow = await startServer(() => {
		// Never respond.
	});
	try {
		process.env.LANGNET_SERVER_URL = `http://127.0.0.1:${slow.port}`;
		await resetMarker();
		const controller = new AbortController();
		const pending = runJsonCommand(['cli', 'langs', '--output', 'json'], 10_000, {
			queued: false,
			signal: controller.signal
		});
		setTimeout(() => controller.abort(), 50);
		await assert.rejects(pending, (error: Error) => error.name === 'AbortError');
		assert.ok(!markerExists(), 'client abort must not trigger a subprocess fallback');
	} finally {
		slow.close();
	}

	console.log('langnet-cli-server-transport: all assertions passed');
}

try {
	await main();
} finally {
	for (const [key, value] of Object.entries(savedEnv)) {
		if (value === undefined) delete process.env[key];
		else process.env[key] = value;
	}
	spawnSync('rm', ['-rf', tmpDir]);
}
