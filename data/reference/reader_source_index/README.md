# Reader Source Index Flat Files

Generated from `data/build/reader/catalog.duckdb`. These files are flat, grep-friendly snapshots of imported reader works by source collection.

## Files

- `all_collections.tsv`: every imported work/edition/artifact provenance row.
- `<collection_id>.tsv`: the same rows split by source collection.
- `duplicate_canonical_text_ids.tsv`: canonical text ids currently attached to more than one visible work.

## Collection summary

| Collection | Works | Editions | Segments | Words | File |
| --- | ---: | ---: | ---: | ---: | --- |
| `digiliblt` | 390 | 390 | 112104 | 6575222 | `digiliblt.tsv` |
| `first1kgreek` | 1082 | 1082 | 249835 | 29482870 | `first1kgreek.tsv` |
| `opengreekandlatin_church_fathers` | 3 | 3 | 232 | 150757 | `opengreekandlatin_church_fathers.tsv` |
| `opengreekandlatin_csel` | 264 | 264 | 85726 | 9770722 | `opengreekandlatin_csel.tsv` |
| `opengreekandlatin_latin` | 7 | 7 | 1828 | 137779 | `opengreekandlatin_latin.tsv` |
| `opengreekandlatin_patrologia` | 1275 | 1275 | 210395 | 25203407 | `opengreekandlatin_patrologia.tsv` |
| `patrologia_graeca_pilot` | 1 | 1 | 14 | 3059 | `patrologia_graeca_pilot.tsv` |
| `patrologia_latina_wikisource` | 14 | 14 | 3744 | 431555 | `patrologia_latina_wikisource.tsv` |
| `perseus` | 1102 | 1102 | 555289 | 15929305 | `perseus.tsv` |
| `phi` | 784 | 784 | 528855 | 4150071 | `phi.tsv` |
| `sanskrit_dcs` | 268 | 268 | 1070138 | 5898557 | `sanskrit_dcs.tsv` |
| `sanskrit_json` | 58 | 58 | 223392 | 1840001 | `sanskrit_json.tsv` |
| `sanskrit_texts` | 320 | 320 | 1021581 | 7405620 | `sanskrit_texts.tsv` |
| `tlg` | 5024 | 5024 | 5313782 | 43445568 | `tlg.tsv` |

## Columns

- `collection_id`
- `language`
- `work_id`
- `title`
- `author`
- `author_id`
- `source_id`
- `cts_work_urn`
- `canonical_text_id`
- `edition_id`
- `edition_label`
- `source_path`
- `cts_edition_urn`
- `file_role`
- `file_status`
- `source_hash`
- `size_bytes`
- `artifact_count`
- `segment_count`
- `token_count`
- `adapters`
- `artifact_paths`
- `source_witness_count`
- `source_witness_collections`

## Regeneration

```bash
just cli reader source-index-export --output-dir data/reference/reader_source_index --output json
```
