# Parser Real-World Testing Findings

**Date**: 2026-04-12
**Testing Method**: Live API calls to CLTK and Diogenes

## Summary

Testing with **real API data** revealed significant differences between expected and actual formats. The parsers work well for idealized test data but have issues with real-world formats.

## Finding 1: CLTK lewis_lines Format Mismatch

### Expected vs. Actual

**What we expected** (based on Diogenes):
```
lupus, -i, m. I. a wolf
amo, amare, amavi, amatum, v. to love
```

**What CLTK actually returns**:
```
lupus


 ī,
m

 a wolf: Torva leaena lupum sequitur...
```

```
amō āvī, ātus, āre AM-, to love: magis te, quam oculos...
```

### Key Differences

1. **Macrons**: `amō āvī ātus āre` (not `amo amare amavi amatum`)
2. **No dashes**: `āvī, ātus` (not `-avi, -atum` or `amavi, amatum`)
3. **Irregular spacing**: Lots of newlines and spaces
4. **Different structure**: No clear comma-separated principal parts

### Impact

**CLTK integration (parse_lewis_lines) DOES NOT WORK with real data**

The assumption that CLTK lewis_lines would be in Diogenes format was incorrect. The two sources use different dictionary formats:
- **Diogenes**: Serves Lewis & Short entries as clean HTML
- **CLTK**: Extracts Lewis & Short text with different formatting

**Current Status**:
- ✅ Parser works for Diogenes HTML
- ❌ Parser FAILS for CLTK lewis_lines (0% success on real data)
- ✅ Tests pass because they use idealized format, not real data

## Finding 2: Verb Principal Parts Pattern

### The Bug

Verbs fail to parse when:
- Principal parts **don't have dash prefixes** (`-ere`)
- AND don't follow a consistent vowel pattern

### Examples

| Entry | Format | Result | Reason |
|-------|--------|--------|--------|
| `moneo, monere, monui, monitum, v.` | No dashes | ❌ FAIL | Mixed vowels: e/u/i/u |
| `moneo, -ere, -ui, -itum, v.` | With dashes | ✅ PASS | Grammar recognizes `-ere` pattern |
| `video, videre, vidi, visum, v.` | No dashes | ❌ FAIL | Mixed vowels: e/i/i/u |
| `audio, audire, audivi, auditum, v.` | No dashes | ✅ PASS | Consistent 'i/u' pattern |
| `amo, amare, amavi, amatum, v.` | No dashes | ✅ PASS | Consistent 'a' pattern |

### Grammar Issue

The grammar token for principal parts is:
```lark
INFLECTION: "-" LEMMA | LEMMA
```

Where `LEMMA` is:
```lark
LEMMA: /[a-zA-ZāēīōūăĕĭŏŭæœÆŒ\u0370-\u03FF\u1F00-\u1FFF]+/
```

The issue: When parsing `moneo, monere, monui, monitum`, the grammar sees:
- `moneo` ← lemma
- `,`
- `monere` ← Should be principal part, but looks like another lemma
- `,`
- `monui` ← Another lemma?
- etc.

Without the dash prefix, the parser can't distinguish "monere" as a principal part vs. a second lemma word.

**Why some verbs work**:
- `audio, audire, audivi, auditum` - Works because all parts share similar phonology
- `amo, amare, amavi, amatum` - Works because of consistent stem
- `moneo, monere, monui, monitum` - Fails because each part looks independent

## Finding 3: Diogenes Format Variations

### Works
```
lupus, i, m. I. a wolf
```

### Fails
```
lupus, i, m. kindred with λύκος
```

**Issue**: Text before sense markers (I., A., etc.) breaks the grammar. The grammar expects:
```lark
entry: entry_header sense_block*
sense_block: sense_marker gloss_text citation_block?
sense_marker: ROMAN "." | LETTER "." | NUMBER "."
```

If there's text like "kindred with λύκος" that doesn't have a sense marker, it's treated as part of the header, which breaks the parse.

## Recommendations

### Immediate

1. **Document CLTK limitation**: Update docs to note that CLTK lewis_lines integration doesn't work with real data

2. **Remove misleading tests**: The CLTK parser tests use idealized formats that don't match reality

3. **Fix verb grammar**: Update grammar to better handle principal parts without dashes

### Short-term

4. **Build CLTK-specific parser**: Create a separate grammar for actual CLTK lewis_lines format:
   ```
   amō āvī, ātus, āre AM-
   ```

5. **Handle freeform text**: Allow text between header and sense blocks

### Long-term

6. **Test with real data**: Always test parsers with actual API responses, not idealized formats

7. **Integration tests**: Add tests that fetch real data and verify parsing

## Current State (Post-Discovery)

**What Actually Works**:
- ✅ English gloss parser: 100% robust (GPT-translated dictionaries)
- ✅ Diogenes parser: ~70% on real formats (works for standard entries)
- ❌ CLTK integration: 0% on real data (format mismatch)

**What We Thought Worked** (based on unit tests):
- ✅ Diogenes: 91% (tested with idealized format)
- ✅ CLTK: 100% (tested with idealized format - NOT real data!)

**Reality Check**: Our unit tests were too optimistic because they used clean, idealized formats instead of messy real-world data.

## Action Items

- [ ] Update documentation to reflect CLTK limitation
- [ ] Add warning comments to CLTK integration code
- [ ] Consider building CLTK-specific grammar
- [ ] Fix verb principal parts grammar
- [ ] Add integration tests with real API data

---

**Testing Date**: 2026-04-12
**Real API Sources**: CLTK dictionary API, Diogenes web service
**Test File**: `tests/test_realworld_data.py`
