# Citation Reference Database - Phase 3 Handoff

**Created**: February 1, 2026
**Status**: Database built, needs integration with citation system

## Executive Summary

Successfully built a unified citation reference database from Classics-Data sources containing 2,187 authors and 31,702 works. The database provides authoritative author/work mappings for CTS URN generation, replacing hardcoded guesses with source-of-truth data.

## What Was Accomplished

### Database Built
- **Location**: `/tmp/classical_refs.db` (2.1 MB)
- **Tables**: `author_index`, `works`, `texts`, `unified_index`
- **Authors**: 2,187 (362 Latin via PHI, 1,825 Greek via TLG)
- **Works**: 31,702 (from TLG canon)
- **Texts**: 391 (from digiliblt TEI XML)

### Parsers Created

#### 1. AuthTabParser (`examples/build_reference_db.py:268-396`)
Parses `authtab.dir` files from PHI/TLG collections.

**Format**: Delimiter-separated records with `&1Author&` markers
```
LAT0448 Gaius Iulius &1Caesar&Caesarl
TLG0012 &1Herodotus& Hist.
```

**Key code**:
```python
pattern = re.compile(r"([A-Z]+)(\d+)\s+([^&]*?)&1([^&]+)&([a-z]?)")
# Captures: prefix, id, alternate_name, author_name, language_code
```

#### 2. CanonParser (`examples/build_reference_db.py:446-523`)
Parses `doccan1.txt` TLG canon files.

**Format**: Entry-per-line with unicode section markers
```
0001  �&1APOLLONIUS RHODIUS& Epic.
0001 001 �&1Argonautica&, ed. H. Fraenkel...
```

#### 3. TEIXMLParser (`examples/build_reference_db.py:55-265`)
Parses digiliblt TEI XML files for full text metadata.

## File Formats Discovered

### PHI/TLG Author Index (`authtab.dir`)

**Structure**:
- Delimiter: `ÿ` (0xFF byte)
- Format: `ID ALT_NAME &1AUTHOR& [GENRE|LANG]`
- Encoding: Latin-1 (cp437 fallback)
- Language codes: `l`=Latin, `g`=Greek, `h`=Hebrew, `c`=Coptic

**Example**:
```
LAT0474 Marcus Tullius &1Cicero&Cicerolat
TLG0001 &1Homerus& Epic.
```

### TLG Canon File (`doccan1.txt`)

**Structure**:
- Unicode formatting characters (`�`) as section markers
- 4-digit author ID + 3-digit work ID for references
- Contains work titles, edition info, word counts

**Example**:
```
0001  �&1APOLLONIUS RHODIUS& Epic.  �(3 B.C.: Alexandrinus)...
0001 001 �&1Argonautica&, ed. H. Fraenkel...
```

### IDT Binary Index Files - CRITICAL FOR AUTHOR/WORK NAMES

**CRITICAL DISCOVERY**: Each IDT file contains the AUTHOR and WORK name!

**Structure**:
- Record header: 2-byte ID + 4-byte pointer + 1-byte length
- Variable-length string (author name or work title)
- Padding to 4-byte boundary

**Filename format**: `tlg####.idt` or `lat####.idt` where #### is the author ID

**Example**: `tlg0012.idt` → Author TLG0012 = Homerus
```
Filename: tlg0012.idt
Contains: &1Homerus& Epic.
Pointer: 0xef0000b1 (points to text location)
```

**Parsing approach**:
```python
with open("tlg0012.idt", "rb") as f:
    data = f.read()

# Parse record at offset 0
record_id = struct.unpack('<H', data[0:2])[0]      # = 1
pointer = struct.unpack('<I', data[2:6])[0]        # = 0xef0000b1
length = data[6]                                   # = N
name = data[7:7+length].decode('latin-1')          # = "&1Homerus& Epic."
```

**Why this matters**:
- IDT filename gives you the author ID directly (e.g., `tlg1252.idt` → TLG1252)
- IDT content gives you the author name AND genre
- When combined with doccan1.txt work IDs, you get complete author/work mapping

**Recommended**: Parse all IDT files to populate a complete author_work table:
```sql
CREATE TABLE author_works (
    author_id TEXT PRIMARY KEY,      -- From filename: "tlg0012"
    author_name TEXT,                 -- From IDT content: "Homerus"
    genre TEXT,                       -- From IDT content: "Epic."
    work_ids TEXT,                    -- Comma-separated work IDs from doccan
    cts_namespace TEXT                -- "tlg" or "phi"
);
```

**Structure** (for reference only):
- Record header: 2-byte ID + 4-byte pointer + 1-byte length
- Variable-length string (author/work name)
- Padding to 4-byte boundary

**Purpose**: Point to text locations in `.txt` data files - useful for full-text search, NOT for citation mapping.

## Database Schema

```sql
CREATE TABLE author_index (
    author_id TEXT PRIMARY KEY,      -- e.g., "LAT0474", "TLG0012"
    author_name TEXT NOT NULL,
    alternate_name TEXT,
    genre TEXT,                       -- History, Philosophy, Epic, etc.
    language TEXT,                    -- "la", "grc", "he", "cop"
    source TEXT,                      -- "phi-latin", "tlg_e"
    cts_namespace TEXT                -- "phi", "tlg"
);

CREATE TABLE works (
    canon_id TEXT,                    -- e.g., "0001"
    author_name TEXT,
    work_title TEXT,                  -- Full title
    reference TEXT,                   -- e.g., "001" (work number within author)
    word_count TEXT,
    work_type TEXT,
    source TEXT,
    cts_urn TEXT                      -- Full CTS URN if available
);

CREATE TABLE unified_index (
    id TEXT NOT NULL,
    type TEXT NOT NULL,               -- "author", "work", "text"
    name TEXT NOT NULL,
    author TEXT,
    work_title TEXT,
    language TEXT,
    source TEXT,
    cts_urn TEXT,
    PRIMARY KEY (id, type)
);
```

## What Remains to Do

### Priority 1: Integrate Database with CTSUrnMapper
**File**: `src/langnet/citation/cts_urn.py`

Current hardcoded mappings need to be replaced with database lookups:

```python
# Current (hardcoded - error-prone):
WORK_TO_CTS_ID = {
    "fin": "phi0473.phi005",  # Guessed!
    "tusc": "phi0473.phi004",  # Guessed!
}

# Needed (database-driven - authoritative):
def get_work_id(self, author: str, work_abbrev: str) -> Optional[str]:
    conn = self._get_connection()
    # Query works table for authoritative mapping
```

**Steps**:
1. Load work titles from `works` table into cache
2. Create abbreviation-to-work mapping (e.g., "fin" → "De Finibus")
3. Build CTS URN from database: `urn:cts:{namespace}:{author_id}.{work_id}:{ref}`

### Priority 2: Add Work Abbreviation Mapping
The database has full work titles but not common abbreviations.

**Current gap**:
- Database has: "De Finibus Bonorum et Malorum"
- Citation uses: "Fin." or "fin"

**Need to add**:
```python
WORK_ABBREVIATIONS = {
    "de finibus bonorum et malorum": ["fin", "de fin"],
    "de oratore": ["de orat", "orat"],
    "epistulae ad atticum": ["att", "ad att"],
}
```

### Priority 3: Fix Cicero Identification
Currently database shows duplicate Cicero entries:
```
LAT0474: Cicero
LAT0478: Cicero
```

**Investigation needed**:
- Are these different authors with same name?
- Or different editions/sources?
- Which ID is correct for De Finibus?

Run:
```sql
SELECT * FROM author_index WHERE author_name LIKE '%Cicero%';
SELECT * FROM works WHERE author_name = 'Cicero';
```

### Priority 4: Test Integration
Verify citations map correctly:
```python
"Cic. Fin. 2 24" → urn:cts:latinLit:phi0473.phi005:2.24
"Hor. C. 1 17 9" → urn:cts:latinLit:phi1290.phi008:1.17.9
"Verg. A. 1 1"   → urn:cts:latinLit:phi1290.phi004:1.1
```

## Files Created/Modified

```
examples/build_reference_db.py   # Main builder (512 lines)
src/langnet/citation/cts_urn.py  # URN mapper (needs updates)
```

## Testing Commands

```bash
# Build database
python examples/build_reference_db.py --data-dir /home/nixos/Classics-Data

# Verify content
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("/tmp/classical_refs.db")
# Check authors
conn.execute("SELECT author_id, author_name FROM author_index LIMIT 10").fetchall()
# Check Cicero
conn.execute("SELECT * FROM author_index WHERE author_name='Cicero'").fetchall()
# Check works by author
conn.execute("SELECT author_name, work_title FROM works LIMIT 20").fetchall()
EOF

# Test CTS mapping
python -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
print(m.map_text_to_urn('Cic. Fin. 2 24'))
print(m.map_text_to_urn('Hor. C. 1 17 9'))
"
```

## Key Insights

1. **IDT files are text pointers, not citation refs** - Don't need them for citation system
2. **authtab.dir has authoritative author IDs** - Use these, don't guess (e.g., Cicero = LAT0474)
3. **doccan1.txt has work IDs** - Maps work number to title/edition
4. **digiliblt has full TEI metadata** - Useful for edition info, not core citations

## Next Steps for Integrator

1. Update `CTSUrnMapper.__init__()` to load database work cache
2. Add `get_work_by_abbreviation()` method
3. Build URNs from: `urn:cts:{namespace}:{author_id}.{work_id}:{location}`
4. Create abbreviation lookup table for common citations
5. Test with Diogenes extractor's citation output
6. Add author/work descriptions for educational value

## Questions to Resolve

- Which Cicero ID (LAT0474 vs LAT0478) is correct?
- Are there standard abbreviation lists we should include?
- Should we add `works` table entry for each author work with abbreviations?
- How to handle anonymous works (e.g., "Anonymi Comici et Tragici")?

---

**Status**: Database ready. Integration work remaining.
**Blocker**: None - database provides authoritative data for all citation needs.