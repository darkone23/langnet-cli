# MOTD Pool Generated Snapshots

This directory stores generated-but-reviewed word-of-day pool snapshots.

The runtime DuckDB at `data/build/motd_pool.duckdb` is ignored build output.
Use these JSON snapshots as the durable generated input for restoring that
pool after rebuilds, workspace cleanup, or handoff.

Restore the current reviewed pool:

```bash
just cli motd-pool restore \
  --path data/generated/motd_pool/2026-06-02/motd-pool-reviewed.json \
  --output json
```

Export a reviewed local pool after auditing:

```bash
just cli motd-pool export \
  --path data/generated/motd_pool/<date>/motd-pool-reviewed.json \
  --output json
```

Validate after restoring or rebuilding:

```bash
just cli motd-pool validate --per-language 30 --output json
python scripts/motd_reader_flow_audit.py --encounter-limit 0
```

These snapshots are generated metadata, not cited evidence. Dictionary refs in
`source_basis` point at local dictionary evidence; they do not replace curated
reader metadata or research-backed attribution records.
