# Whitaker's Words Test Data

Sample output from Whitaker's Words used during parser development.

## Files

| File | Format | Content |
|------|--------|---------|
| `senses.txt` | Multi-line dictionary definitions | One sense per line (semicolon-separated for multiple senses) |
| `term-codes.txt` | Morphological code lines | Word + codes + etymology + metadata |
| `term-facts.txt` | Inflection table rows | Word form, POS, declension/conjugation, case/number, etc. |

## Format Details

### senses.txt
Raw dictionary entry lines. Each line may contain multiple senses separated by `;`. Example:
```
woman; female; female child/daughter; maiden; young woman/wife; sweetheart; slavegirl;
```

### term-codes.txt
Morphological breakdown with etymology and notes. Format:
```
word, stem1, stem2, ...  POS  (conjugation/declension)   [XYZXY]    notes
```

Example:
```
amo, amare, amavi, amatus  V (1st)   [XXXAO]  
```

### term-facts.txt
Inflection table with detailed morphological tags. Format:
```
word.form  POS  declension  case number gender  [mood tense voice person]  PPL
```

Example:
```
amor                V      1 1 PRES PASSIVE IND 1 S    
```
