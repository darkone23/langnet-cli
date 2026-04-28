# Semantic Pipeline Diagram

```mermaid
flowchart TD
    A[Lookup Query] --> B[Normalize]
    B --> C[Tool Plan]
    C --> D[Fetch]
    D --> E[Extract]
    E --> F[Derive]
    F --> G[Claims and Triples]
    G --> H[Witness Sense Units]
    H --> I[Sense Buckets]
    I --> J[Optional Hydration]
    J --> K[Learner Output]
```

Implemented today: through exact `Sense Buckets` and first `Learner Output`
via `langnet-cli encounter`.

Next implementation target: better learner display over the existing buckets:
reader-form ranking, compact glosses, and evidence-preserving source details.
