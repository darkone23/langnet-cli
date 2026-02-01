# Velthuis Input Tips for `sktreader`

- The Heritage Platform's `sktreader` CGI script expects **Velthuis** transliteration.
- It is more tolerant of doubled characters that explicitly mark long vowels.
- Example:
  - Sending `agni` (single *i*) often yields poor or no results.
  - Sending `agn**ii**` (double *i* to indicate a long vowel) produces much better results.
- Recommendation: When constructing Velthuis input for `sktreader`, ensure long vowels are represented with doubled characters (`aa`, `ii`, `uu`, `RRi`, `LLi`, `e`, `ai`, `o`, `au` etc.) before making the request.
- This tip can be incorporated into the `fetch_cgi_script` helper or any preprocessing step that builds the `t=VH` parameter.

Additionally:

consider these URL params (for input agnii)

http://localhost:48080/cgi-bin/skt/sktreader?t=VH;lex=SH;font=roma;cache=t;st=t;us=f;text=agnii;topic=;abs=f;corpmode=;corpdir=;sentno=;mode=p;cpts=

useful information on this page, and also:

Color,What it represents,Examples
Green,Substantives,"Nouns, adjectives, and pronouns (Declined forms)."
Blue,Finite Verbs,Conjugated verb forms (Tinnanta).
Cyan (Light Blue),Indeclinables,"Adverbs, particles (avyaya), and preverbs (upasarga)."
Magenta,Compounds,Internal components or segments of a compound (samāsa).
Yellow / Orange,Kridantas,"Participles, infinitives, and absolutives (verbal adjectives/nouns)."
Red,Errors,Unrecognized forms or segments that don't fit the lexicon.

compare to a no match case (input agni):

http://localhost:48080/cgi-bin/skt/sktparser?t=VH;lex=SH;font=roma;cache=t;st=t;us=f;text=agni;topic=;abs=f;corpmode=;corpdir=;sentno=;mode=p;cpts=;n=1

this and more documented at:

http://localhost:48080/manual.html
