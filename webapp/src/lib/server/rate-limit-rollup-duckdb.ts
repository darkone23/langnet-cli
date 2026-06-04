import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { RateLimitRollup } from './rate-limit-rollup';

const tableName = 'rate_limit_rollups';
const defaultDbPath = resolve(process.cwd(), 'data/cache/langnet-rate-limit-rollups.duckdb');
const duckDbBusyRetryAttempts = 5;
const duckDbBusyRetryBaseDelayMs = 25;
let writeQueue: Promise<void> = Promise.resolve();
const schemaColumns = [
	'minute_window_start_epoch_seconds',
	'client_class',
	'attestation_status',
	'attestation_scope',
	'rate_limit_bucket',
	'key_type',
	'key_hash',
	'request_count',
	'cost_sum',
	'would_limit_count',
	'valid_attestation_count',
	'missing_attestation_count',
	'expired_attestation_count',
	'status_2xx_count',
	'status_4xx_count',
	'status_5xx_count',
	'second_bits'
] as const;

const createTableSql = `
CREATE TABLE IF NOT EXISTS ${tableName} (
  minute_window_start_epoch_seconds BIGINT NOT NULL,
  client_class TEXT NOT NULL,
  attestation_status TEXT NOT NULL,
  attestation_scope TEXT NOT NULL,
  rate_limit_bucket TEXT NOT NULL,
  key_type TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  request_count BIGINT NOT NULL,
  cost_sum BIGINT NOT NULL,
  would_limit_count BIGINT NOT NULL,
  valid_attestation_count BIGINT NOT NULL,
  missing_attestation_count BIGINT NOT NULL,
  expired_attestation_count BIGINT NOT NULL,
  status_2xx_count BIGINT NOT NULL,
  status_4xx_count BIGINT NOT NULL,
  status_5xx_count BIGINT NOT NULL,
  second_bits VARCHAR NOT NULL,
  PRIMARY KEY (
    minute_window_start_epoch_seconds,
    client_class,
    attestation_status,
    attestation_scope,
    rate_limit_bucket,
    key_type,
    key_hash
  )
);
`;

function databasePath() {
	return process.env.LANGNET_RATE_LIMIT_ROLLUP_DB_PATH
		? resolve(process.cwd(), process.env.LANGNET_RATE_LIMIT_ROLLUP_DB_PATH)
		: defaultDbPath;
}

async function runSqlWithRetry(sql: string) {
	let lastError: unknown;
	for (let attempt = 0; attempt <= duckDbBusyRetryAttempts; attempt += 1) {
		try {
			execFileSync('duckdb', [databasePath(), '-json', '-c', sql], {
				stdio: ['ignore', 'pipe', 'pipe']
			});
			return;
		} catch (error) {
			lastError = error;
			if (!isTransientDuckDbWriterError(error) || attempt === duckDbBusyRetryAttempts) {
				break;
			}
			await sleep(duckDbBusyRetryBaseDelayMs * 2 ** attempt);
		}
	}
	throw new Error(`DuckDB upsert failed: ${errorMessage(lastError)}`);
}

function isTransientDuckDbWriterError(error: unknown) {
	const message = errorMessage(error).toLowerCase();
	return (
		message.includes('database is locked') ||
		message.includes('could not set lock') ||
		message.includes('conflicting lock') ||
		message.includes('io error') && message.includes('lock')
	);
}

function errorMessage(error: unknown) {
	if (error && typeof error === 'object') {
		const maybeProcessError = error as {
			message?: string;
			stderr?: Buffer | string;
			stdout?: Buffer | string;
		};
		const stderr = maybeProcessError.stderr ? String(maybeProcessError.stderr) : '';
		const stdout = maybeProcessError.stdout ? String(maybeProcessError.stdout) : '';
		return [maybeProcessError.message, stderr, stdout].filter(Boolean).join('\n');
	}
	return String(error);
}

function sleep(ms: number) {
	return new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
}

async function runSql(sql: string) {
	try {
		await runSqlWithRetry(sql);
	} catch (error) {
		throw new Error(`DuckDB upsert failed: ${errorMessage(error)}`);
	}
}

function quoteText(value: string) {
	return `'${value.replaceAll("'", "''")}'`;
}

function rowValues(row: RateLimitRollup) {
	return [
		String(row.minuteWindowStartEpochSeconds),
		quoteText(row.clientClass),
		quoteText(row.attestationStatus),
		quoteText(row.attestationScope),
		quoteText(row.rateLimitBucket),
		quoteText(row.keyType),
		quoteText(row.keyHash),
		String(row.requestCount),
		String(row.costSum),
		String(row.wouldLimitCount),
		String(row.validAttestationCount),
		String(row.missingAttestationCount),
		String(row.expiredAttestationCount),
		String(row.status2xxCount),
		String(row.status4xxCount),
		String(row.status5xxCount),
		quoteText(row.secondBits)
	];
}

function valuesClause(rows: readonly RateLimitRollup[]) {
	return rows.map((row) => `(${rowValues(row).join(', ')})`).join(',\n');
}

export async function upsertRateLimitRollups(rows: readonly RateLimitRollup[]) {
	if (rows.length === 0) return;

	const pendingRows = [...rows];
	writeQueue = writeQueue.then(
		() => writeRateLimitRollups(pendingRows),
		() => writeRateLimitRollups(pendingRows)
	);
	return writeQueue;
}

async function writeRateLimitRollups(rows: readonly RateLimitRollup[]) {
	mkdirSync(dirname(databasePath()), { recursive: true });
	const sql = `
${createTableSql}
INSERT INTO ${tableName} (${schemaColumns.join(', ')})
VALUES ${valuesClause(rows)}
ON CONFLICT (
  minute_window_start_epoch_seconds,
  client_class,
  attestation_status,
  attestation_scope,
  rate_limit_bucket,
  key_type,
  key_hash
) DO UPDATE SET
  request_count = ${tableName}.request_count + EXCLUDED.request_count,
  cost_sum = ${tableName}.cost_sum + EXCLUDED.cost_sum,
  would_limit_count = ${tableName}.would_limit_count + EXCLUDED.would_limit_count,
  valid_attestation_count = ${tableName}.valid_attestation_count + EXCLUDED.valid_attestation_count,
  missing_attestation_count = ${tableName}.missing_attestation_count + EXCLUDED.missing_attestation_count,
  expired_attestation_count = ${tableName}.expired_attestation_count + EXCLUDED.expired_attestation_count,
  status_2xx_count = ${tableName}.status_2xx_count + EXCLUDED.status_2xx_count,
  status_4xx_count = ${tableName}.status_4xx_count + EXCLUDED.status_4xx_count,
  status_5xx_count = ${tableName}.status_5xx_count + EXCLUDED.status_5xx_count,
  second_bits = CAST(${tableName}.second_bits AS BIGINT) | CAST(EXCLUDED.second_bits AS BIGINT)
`;
	await runSql(sql);
}
