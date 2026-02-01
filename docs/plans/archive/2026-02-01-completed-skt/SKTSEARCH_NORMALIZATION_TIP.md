# Using `sktsearch` for Morphological Normalization

**Why it helps**
- The `sktreader` CGI often struggles with short or ambiguously‑encoded inputs (e.g., `agni`).
- `sktsearch` can locate the canonical entry page (e.g., `/skt/MW/2.html#H_agnii`) even when the query is a plain short form.
- By calling `sktsearch` first, we can extract the link that contains the correctly Velthuis‑encoded term (`agn**ii**`).

**Proposed workflow**
1. Query the `sktsearch` endpoint with the raw user term.
2. Parse the returned HTML for any `/skt/MW/...#H_<term>` link.
3. If a link is found, extract the Velthuis term from the fragment identifier (the part after `#H_`).
4. Use that extracted term as the input to `sktreader` (or to any downstream morphology service).
5. Fall back to the original `sktreader` request only if no suitable link is found.

**Benefits**
- Higher recall: more queries return a result because the canonical form is discovered first.
- Better accuracy: the morphology analysis receives a correctly‑encoded term.
- Minimal overhead: `sktsearch` is a lightweight lookup compared to the full morphological parser.

**Next steps**
- Implement a helper `fetch_canonical_via_sktsearch(term: str) -> Optional[str]` in `src/langnet/heritage/client.py`.
- Update the normalization pipeline to call this helper before invoking `fetch_canonical_sanskrit`.
- Add unit tests covering cases like `agni` → `agn**ii**` and ensure the fallback works.
