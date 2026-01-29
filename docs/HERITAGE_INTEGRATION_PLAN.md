# Heritage Platform Integration Plan

## Status: IN PROGRESS - Parser/Response Issues

The Heritage Platform infrastructure is wired and responding, but the parser is not extracting solutions correctly for most words.

## Health Check Status

```
curl http://localhost:8000/api/health
```

```
{
  "status": "healthy",
  "components": {
    "diogenes": {"status": "healthy"},
    "cltk": {"status": "healthy"},
    "spacy": {"status": "healthy"},
    "whitakers": {"status": "healthy"},
    "cdsl": {"status": "healthy"},
    "heritage": {"status": "degraded", "message": "Heritage responding but no solutions"}
  }
}
```

## Fuzz Test Results

| Word | Heritage Solutions | CDSL Entries |
|------|-------------------|--------------|
| agni | 2 | 10 |
| yoga | 0 | 43 |
| deva | 0 | 36 |
| asana | 0 | 23 |

**Problem:** Heritage Platform returns solutions count in metadata (`total_available: 1`) but `solutions` array is empty for most words except "agni".

## Issues Identified

1. **Parser not extracting analyses** - `analyses: []` arrays are empty
2. **Solution count mismatch** - Metadata shows `total_available: 1` but `solutions` array is empty
3. **Word-dependent** - Only "agni" works, others return 0 solutions

## Health Check Added

```python
@staticmethod
def heritage() -> dict:
    """Check Heritage Platform is responding with valid data"""
    try:
        config = HeritageConfig()
        morphology = HeritageMorphologyService(config)
        result = morphology.analyze("agni")
        if result and result.total_solutions > 0:
            return {"status": "healthy", "solutions": result.total_solutions}
        elif result:
            return {"status": "degraded", "message": "Heritage responding but no solutions"}
        else:
            return {"status": "unhealthy", "message": "No result from Heritage"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}
```

## Root Cause Analysis

The Heritage Platform (`sktreader` CGI) is returning HTML, but the `SimpleHeritageParser` is not correctly parsing the solution structure:

```json
// Current response (broken)
{
  "morphology": {
    "input_text": "yoga",
    "solutions": [],
    "total_solutions": 0,
    "metadata": {"total_available": 1}
  }
}

// Expected response (goal)
{
  "morphology": {
    "input_text": "yoga",
    "solutions": [
      {
        "type": "morphological_analysis",
        "analyses": [
          {
            "word": "yoga",
            "lemma": "yuj",
            "pos": "noun",
            ...
          }
        ],
        "total_words": 1
      }
    ],
    "total_solutions": 1
  }
}
```

## Next Steps

1. **Debug HTML format** - Log raw HTML from Heritage Platform to understand structure
2. **Fix SimpleHeritageParser** - Update regex patterns and HTML traversal
3. **Test with "agni"** - Understand why it works for this word
4. **Verify all words** - Ensure parser extracts solutions for all Sanskrit words

## Environment Variables

```bash
HERITAGE_URL="http://localhost:48080"   # Heritage Platform base URL
HTTP_TIMEOUT="30"                       # HTTP request timeout
```

## Test Commands

```bash
# Health check
curl http://localhost:8000/api/health

# Sanskrit query with Heritage
curl -X POST "http://localhost:8000/api/q" -d "l=san&s=agni"

# Sanskrit query without Heritage
curl -X POST "http://localhost:8000/api/q" -d "l=san&s=yoga"
```

## Integration Tests

Real integration tests added in `tests/test_heritage_real_integration.py`:
- Skip gracefully if Heritage unavailable
- Verify morphology analysis returns solutions
- Check response times are reasonable

## Fallback Behavior

If Heritage Platform is unavailable or returns no solutions:
- `_query_sanskrit` continues to CDSL fallback
- User gets CDSL results only (backward compatible)
