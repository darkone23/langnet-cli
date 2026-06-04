import { rmSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { strict as assert } from 'node:assert';
import { buildRateLimitObservation, type RateLimitObservationInput } from './rate-limit-rollup';
import type { RateLimitDecision } from './rate-limit';
import type { AttestationScope } from '$lib/attestation-scope';
import { upsertRateLimitRollups } from './rate-limit-rollup-duckdb';

const dbPath = resolve(process.cwd(), `data/cache/langnet-rate-limit-rollups-test-${randomBytes(8).toString('hex')}.duckdb`);
process.env.LANGNET_RATE_LIMIT_ROLLUP_DB_PATH = dbPath;

type RateLimitRow = {
	request_count: number;
	cost_sum: number;
	would_limit_count: number;
	valid_attestation_count: number;
	missing_attestation_count: number;
	expired_attestation_count: number;
	status_2xx_count: number;
	status_4xx_count: number;
	status_5xx_count: number;
};

const attestationScope: AttestationScope = 'search';

function makeDecision(clientClass: string, wouldLimit = false): RateLimitDecision {
	return {
		mode: 'observe',
		wouldLimit,
		keyType: 'anonymous_session',
		bucket: `bucket:${clientClass}`,
		limit: 1000,
		remaining: 1000,
		used: 0,
		windowSeconds: 60
	};
}

function buildInput(overrides: Partial<RateLimitObservationInput> = {}) {
	return {
		status: 200,
		requestCost: 1,
		clientClass: 'trusted_web_session' as const,
		attestationStatus: 'valid' as const,
		attestationScope,
		rateLimitDecision: makeDecision('trusted_web_session'),
		keyType: 'anonymous_session' as const,
		principal: 'duckdb-principal',
		...overrides
	};
}

function queryDuckDb<T>(sql: string): Promise<T[]> {
	return new Promise((resolve, reject) => {
		try {
			const output = execFileSync('duckdb', ['-readonly', dbPath, '-json', '-c', sql])
				.toString()
				.trim();
			if (!output) {
				resolve([]);
				return;
			}
			resolve(JSON.parse(output) as T[]);
		} catch (error) {
			reject(new Error(`DuckDB query failed: ${String(error)}`));
		}
	});
}

try {
	const first = buildRateLimitObservation(buildInput({ status: 200, requestCost: 5, observedAtEpochSeconds: 1000 }));
	const second = buildRateLimitObservation(
		buildInput({ status: 404, requestCost: 3, observedAtEpochSeconds: 1005, rateLimitDecision: makeDecision('trusted_web_session', true) })
	);

	await upsertRateLimitRollups([first]);
	await upsertRateLimitRollups([second]);

	const rows = await queryDuckDb<RateLimitRow>(
		"SELECT request_count, cost_sum, would_limit_count, valid_attestation_count, missing_attestation_count, expired_attestation_count, status_2xx_count, status_4xx_count, status_5xx_count FROM rate_limit_rollups WHERE rate_limit_bucket = 'bucket:trusted_web_session'"
	);
	assert.equal(rows.length, 1);
	assert.equal(rows[0].request_count, 2);
	assert.equal(rows[0].cost_sum, 8);
	assert.equal(rows[0].would_limit_count, 1);
	assert.equal(rows[0].status_2xx_count, 1);
	assert.equal(rows[0].status_4xx_count, 1);
	assert.equal(rows[0].valid_attestation_count, 2);
	assert.equal(rows[0].missing_attestation_count, 0);
	assert.equal(rows[0].expired_attestation_count, 0);
} catch (error) {
		rmSync(dbPath, { force: true });
		throw error;
	}

{
	const rows = await queryDuckDb<{ name: string }>(`SELECT name FROM pragma_table_info('rate_limit_rollups')`);
	const hasPrincipal = rows.some((row) => row.name === 'principal');
	assert.equal(hasPrincipal, false);
}

rmSync(dbPath, { force: true });

console.log('rate-limit rollup duckdb adapter checks complete');
