> some more iteration is probably helpful on making a unified output

current data sources
  - cltk backends
  - cdsl indexer / db
  - perseus data CTS urns
  - heritage platform
  - foster data mapping
  - abbreviation maps
  - diogenes

we generally are returning dictionary entries
  - sometimes those entries have part of speech parsing
  - sometimes those entries have structured output graphs
  - generally takes time to load (metadata)

we should consider each individual tool output and how to best integrate its ouput

we want a stable 'cli query ...' schema quite soon

the python types are best when easily mapped to things like avro structs
thus clear datatypes are preferred

create UI plan for citations

-> use a tool like ddg / ducky:
  - eg: https://duckduckgo.com/?q=!ducky+urn:cts:latinLit:phi0119.phi008
    -> https://catalog.perseus.tufts.edu/catalog/urn:cts:latinLit:phi0119.phi008

consider outbound searches:
- http://www.sanskrit-linguistics.org/dcs/index.php?contents=abfrage&word=nirodha&query_type=1&sort_by=alpha
- http://www.sanskrit-linguistics.org/dcs/index.php?contents=impressum
- https://github.com/OliverHellwig/sanskrit
