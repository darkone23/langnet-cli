# Server Fix Required - Citation Processing Bug

## Problem Summary
The langnet-cli server's citation processing functionality is broken, causing 500 Internal Server Errors for all API queries that involve citations.

## Root Cause
The error occurs in `src/langnet/asgi.py` in the `_add_citations_to_response()` function. When processing citations, the code tries to access `citation.references[0].cts_urn` but fails with the error `'dict' object has no attribute 'references'`.

## Specific Error Details
- **Error Message**: `'dict' object has no attribute 'references'` (or sometimes `'dict' object has no attribute 'short_title'`)
- **Location**: `src/langnet/asgi.py` lines 210-225 (in the citation processing loop)
- **Function**: `_add_citations_to_response()` 
- **Context**: The function is trying to process Citation objects but they're being converted to dictionaries somewhere in the pipeline

## Current Workaround
I temporarily disabled citation processing in `src/langnet/asgi.py` by commenting out the `_add_citations_to_response()` call. This allows the server to respond to basic queries but without citation functionality.

## What Was Being Done
I was reorganizing the documentation structure (consolidating 66 files to ~40 files) and made changes to the ASGI file to add debugging and fix citation processing. I incorrectly tried to restart the server using direct bash commands instead of the proper `just` recipe.

## Server Status
- Server startup process works (takes ~20 seconds to load all libraries)
- Basic server functionality works (health endpoint returns 200 OK)
- Citation processing is disabled (temporary workaround in place)
- Need to restart server with proper `just` recipe after fix

## Files That Need Attention
1. **`src/langnet/asgi.py`** - Fix the citation processing bug and re-enable functionality
2. Server restart using proper `just` recipe

## Fix Strategy Needed
1. Identify where Citation objects are being converted to dictionaries
2. Fix the attribute access in `_add_citations_to_response()` function
3. Ensure proper serialization of Citation objects through ORJsonResponse
4. Test with real API queries
5. Restart server using proper `just` commands
6. Re-enable citation processing

## Technical Context
- The citation system uses dataclass models (`Citation`, `TextReference`) from `src/langnet/citation/models.py`
- The CTS URN mapper in `src/langnet/citation/cts_urn.py` expects Citation objects
- The ORJsonResponse uses `orjson.dumps()` for serialization
- The error suggests the objects are being converted to dicts before processing but the code still tries to access them as objects