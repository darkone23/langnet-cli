# MOTD Pool Reader-Flow Audit

`data/build/motd_pool.duckdb` is ignored build output. The durable reviewed
input is the generated snapshot under `data/generated/motd_pool/`.

Stable restore path:

```bash
just cli motd-pool restore \
  --path data/generated/motd_pool/2026-06-02/motd-pool-reviewed.json \
  --output json
just cli motd-pool validate --per-language 30 --output json
```

Operational audit:

```bash
python scripts/motd_reader_flow_audit.py --encounter-limit 0
```

Target high-risk rows with encounter and briefing checks:

```bash
python scripts/motd_reader_flow_audit.py \
  --query gar --query horao --query nux --query eo \
  --query jñāna --query kar --query darshan --query hast \
  --encounter-limit 20 \
  --output examples/debug/motd-reader-flow-audit-risk.json
```

The audit flags operational reader-flow issues:

- missing or failed word-index wheel anchors
- generated pool summaries/short glosses that leak Greek source text
- empty stored `source_basis[].source_ref`
- encounter/briefing errors
- noisy brief refs such as bare abbreviations

If a local repair is accepted, export the reviewed runtime pool back into a
tracked snapshot:

```bash
just cli motd-pool export \
  --path data/generated/motd_pool/<date>/motd-pool-reviewed.json \
  --output json
```
