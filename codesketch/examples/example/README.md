# Examples

Example scripts demonstrating langnet-cli functionality. These scripts may download CLTK language models on first run.

## Examples

| File | Purpose | Data Dependency |
|------|---------|-----------------|
| `cltk_pipeline_example.py` | CLTK NLP pipeline demo for Greek and Sanskrit | Downloads ~500MB CLTK models on first run |
| `whitakers_parsers_example.py` | Interactive demo of individual line parsers (facts, codes, senses) | Uses local test data |
| `whitakers_words_example.py` | Bulk query of ~500 Latin words via Whitaker's Words | Local whitakers-words binary |

## Running Examples

```bash
# CLTK pipelines (downloads models on first run)
python tests/example/cltk_pipeline_example.py

# Whitaker's parser demonstration
python tests/example/whitakers_parsers_example.py

# Large Latin word batch query
python tests/example/whitakers_words_example.py
```

## Notes

- `cltk_pipeline_example.py` requires network access to download CLTK language models (~500MB for Latin models, which are currently disabled due to compatibility issues)
- `whitakers_parsers_example.py` uses sample data from `tests/data/whitakers-lines/` for testing parser logic
- `whitakers_words_example.py` requires `whitakers-words` binary to be installed locally
