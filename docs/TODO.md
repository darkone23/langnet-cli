known issues to be resolved:

### diogenes integration issues

- sense extraction from diogenes often results in broken senses
  - usually 'dictionary sense' and a bunch of 'about this usage'
- citations should return proper CTS URNs
  - CTS URN enrichment currently not working

### heritage platform integration issues

- sanskrit terms often need canonical form via sktsearch
  - e.g agni -> agnii or vrika -> vṛka
- all san tools should use the 'canonical form'
- citation abbreviations not including corpus abbr.
  - saved real abbr list to ./upstream-docs/skt-heritage/ABBR.md
- sktsearch not wired into tools
  - no DICO dict integration yet

### CDSL issues

- often SLP1 encoded text in the definitions
  - would probably take an automated pipeline to fix
    - eg tokenize -> transliterate -> lookup -> replace if valid sanskrit term

> example:
>  vf/kA   (A), f. a kind of plant (= ambazWA), L.
>  vṛ̍kā    (A), f. a kind oṛ plant (= ambaṣṭhā), L.

### common issues

- universal schema issues
  - created at in CDSL citation seems pointless
  - mapping to universal schema often broken
  - needs better hierarchical organization for related / grouped terms
- tools for debug
  - tool output should just be passthrough json
  - tool should have standard 'verbs'
- functional grammar mapping often not present

### needs a web ui

- data accuracy bugs are often easer to spot via manual fuzzing
