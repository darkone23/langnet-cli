- dictionary parsers
  - LSJ from diogenes
  - MW from CDSL
  - lewis lines from CLTK

- DICO integration
  - extraction / basic parser
  - translation pipeline
  - dictionary / pos parser

- bucketing of dictionary entries
  - dict entries as witnesses for 'semantic facts'

- text normalization for CDSL
  - normalize to IAST
  - represent information where necessary

- make pos plural (noun, adjective, masc, fem)
  - eg. shiva

- define semantic atom
  - word candidates are plural
  - dictionaries / linguistic stemmers are 'evidence/witnesses'

```python
class LexemeCore:
    lemma: str
    language: str
    
    pos: str
    inflectional_family: Optional[str]
    
    semantic_clusters: List[SemanticCluster]
    core_gloss: str
    
    domains: List[str]  # philosophy, ritual, grammar, etc.
    
    cross_refs: List[str]
    citations: List[Citation]
```

cf a 'claim' about a lexeme

```typescript
Claim {
  subject: LexemeID
  predicate: string (namespaced)
  value: string | object
  witness: WitnessID
  metadata?: {confidence?, raw?}
}
```

'claim types':
pos
sense
entity_type
register
morph.case
morph.number
morph.gender
etymology
citation
note

example output for a query like `shiva`:

```json
{
  "query": {"surface": "shiva", "language_hint": "san"},
  "candidates": [
    {
      "lexeme_id": "san:śiva",
      "display": "śiva",
      "pos_hypotheses": [
        {"pos": "adjective", "confidence": 0.72},
        {"pos": "noun", "confidence": 0.95}
      ],
      "core_sense_buckets": [
        {
          "bucket_id": "B1",
          "gloss": "auspicious; benign; favorable (quality)",
          "register": ["general", "epithet"],
          "witnesses": [
            {"source": "MW", "sense_refs": ["217497"]},
            {"source": "AP90", "sense_refs": ["27998:1"]},
            {"source": "heritage", "sense_refs": ["mw:śiva(mf n)"] }
          ]
        },
        {
          "bucket_id": "B2",
          "gloss": "Śiva (deity, proper name / title)",
          "register": ["mythology", "religion"],
          "witnesses": [
            {"source": "MW", "sense_refs": ["217501"]},
            {"source": "AP90", "sense_refs": ["27998:vaH"] }
          ]
        },
        {
          "bucket_id": "B3",
          "gloss": "welfare; prosperity; blessing (abstract noun)",
          "register": ["abstract"],
          "witnesses": [
            {"source": "MW", "sense_refs": ["217499", "217531"]},
            {"source": "AP90", "sense_refs": ["27998:vaM"] }
          ]
        }
      ],
      "morphology_observed": [
        {
          "analysis": {"case": "vocative", "number": "singular", "gender": "masculine"},
          "witnesses": [{"source": "heritage", "ref": "morph:ziva"}],
          "note": "Observed form likely used in address; doesn’t force lemma POS to be only noun."
        }
      ],
      "warnings": [
        "Many minor botanical/technical senses exist in MW; hidden by default."
      ]
    }
  ]
}
```

"the graph" aka prolog ate my data

```
(san:śiva)  hasWitness          (mw:217497)
(mw:217497) assertsSense        "auspicious; benign; favorable"
(mw:217497) assertsPOS          "adj"
(mw:217497) assertsPOS          "noun"

(san:śiva)  hasWitness          (mw:217501)
(mw:217501) assertsEntityType   "deity"
(mw:217501) assertsSense        "Śiva (Trimūrti...)"

(san:śiva)  hasWitness          (heritage:morph:ziva)
(heritage:morph:ziva) assertsMorph.case    "vocative"
(heritage:morph:ziva) assertsMorph.gender  "masculine"
(heritage:morph:ziva) assertsMorph.number  "singular"
```

example cli output:

```txt
> cli word shiva --lang san

Candidate: śiva   (san:śiva)

Top meanings (reduced):
  1) "auspicious; benign; favorable"  [MW, AP90]
  2) "Śiva (the deity)"              [MW, AP90]
  3) "welfare; prosperity; blessing" [MW, AP90]

Morphology observed (from Heritage for input ziva):
  vocative singular masculine  (likely address form)

More:
  - many minor senses exist (plants, substances, etc.) [MW]
```
