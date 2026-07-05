# Frontend Architecture

Project Orion is the public SvelteKit frontend for the internal `langnet-cli`
runtime. The web app is intentionally thin at the backend boundary: browser
routes own URL state and interaction state, SvelteKit API routes adapt requests
to CLI JSON commands, and reusable surface modules under `webapp/src/lib/`
handle transformation, orchestration, and rendering.

## Route And Data Boundary

```mermaid
flowchart TB
    subgraph Browser["Browser routes"]
        Home["/"]
        DeskPage["/q word desk"]
        ReaderPage["/reader reader desk"]
        LibraryPage["/library discovery"]
        LearnPage["/learn morphology learning"]
    end

    subgraph SurfaceLib["Svelte surface libraries"]
        DeskLib["src/lib/desk controllers and components"]
        ReaderLib["src/lib/reader loaders and components"]
        PublicLib["src/lib/public and shared Orion primitives"]
        CopyLib["shared copy, types, display helpers"]
    end

    subgraph ApiRoutes["SvelteKit API adapter routes"]
        SearchApi["/api/search"]
        EncounterApi["/api/encounter-briefing"]
        ReaderApi["/api/reader"]
        WordIndexApi["/api/word-index"]
        ParadigmApi["/api/paradigm"]
        MotdApi["/api/motd"]
        CacheApi["/api/translation-cache"]
    end

    subgraph ServerAdapters["Server-only adapters"]
        LangnetCli["src/lib/server/langnet-cli.ts"]
        ReaderCli["src/lib/server/reader-cli.ts"]
        ReaderCache["src/lib/server/reader-cache.ts"]
    end

    subgraph Runtime["Internal langnet-cli runtime"]
        Cli["langnet.cli main"]
        ReaderStore["reader catalog and passage stores"]
        WordStores["dictionary, word-index, paradigm, and cache stores"]
    end

    Home --> PublicLib
    DeskPage --> DeskLib
    ReaderPage --> ReaderLib
    LibraryPage --> ReaderLib
    LearnPage --> PublicLib
    DeskLib --> CopyLib
    ReaderLib --> CopyLib
    PublicLib --> CopyLib

    DeskLib --> SearchApi
    DeskLib --> WordIndexApi
    DeskLib --> ParadigmApi
    DeskLib --> MotdApi
    DeskLib --> CacheApi
    ReaderLib --> ReaderApi
    ReaderLib --> SearchApi
    ReaderLib --> EncounterApi

    SearchApi --> LangnetCli
    EncounterApi --> LangnetCli
    WordIndexApi --> LangnetCli
    ParadigmApi --> LangnetCli
    MotdApi --> LangnetCli
    CacheApi --> LangnetCli
    ReaderApi --> ReaderCli
    ReaderApi --> ReaderCache

    LangnetCli --> Cli
    ReaderCli --> Cli
    Cli --> ReaderStore
    Cli --> WordStores
```

## Word Desk Surface

The `/q` route composes one route controller and many extracted modules. The
remaining route-owned work should stay limited to Svelte state assignment,
URL synchronization, and top-level request sequencing.

```mermaid
flowchart TB
    DeskRoute["/q route"] --> DeskController["DeskRouteController.svelte"]
    DeskController --> DeskShell["DeskPageShell.svelte"]
    DeskController --> DeskTopbar["DeskTopbar.svelte"]
    DeskController --> DeskHero["DeskHeroSearch.svelte"]
    DeskController --> DeskResults["DeskLookupResults.svelte"]
    DeskController --> DeskSidebar["DeskSidebar.svelte"]

    subgraph DeskControllers["Desk orchestration modules"]
        RouteState["desk-route.ts"]
        StorageController["desk-route-storage-controller.ts"]
        Workflows["desk-workflows.ts"]
        Activity["desk-activity.ts"]
        MotdController["desk-motd-controller.ts"]
        ParadigmController["desk-paradigm-controller.ts"]
        WordIndex["desk-word-index.ts"]
        ToolFilters["desk-tool-filters.ts"]
        ViewState["desk-view-state.ts"]
    end

    subgraph DeskPureHelpers["Desk pure helpers"]
        Lookup["desk-lookup.ts"]
        Entry["desk-entry.ts"]
        Status["desk-status.ts"]
        Session["desk-session.ts"]
        Motd["desk-motd.ts"]
        Paradigm["desk-paradigm.ts"]
        Endpoints["desk-endpoints.ts"]
        Oracle["desk-oracle.ts"]
    end

    subgraph DeskComponents["Desk component cluster"]
        ResultsCard["DeskDictionaryGroupCard.svelte"]
        ComponentLedger["DeskComponentLedger.svelte"]
        WordIndexRail["DeskWordIndexRail.svelte"]
        MotdFolio["DeskMotdFolio.svelte"]
        ActivityLedger["DeskActivityLedger.svelte"]
        ParadigmPanel["DeskParadigmPanel.svelte"]
        OracleTrace["DeskOracleTrace.svelte"]
    end

    DeskController --> RouteState
    DeskController --> StorageController
    DeskController --> Workflows
    DeskController --> Activity
    DeskController --> MotdController
    DeskController --> ParadigmController
    DeskController --> WordIndex
    DeskController --> ToolFilters
    DeskController --> ViewState
    DeskController --> DeskPureHelpers
    DeskResults --> DeskComponents
    DeskSidebar --> DeskComponents

    RouteState --> Endpoints
    Workflows --> Lookup
    Workflows --> Endpoints
    WordIndex --> Endpoints
    StorageController --> Session
    ResultsCard --> Entry
    ResultsCard --> Status
    OracleTrace --> Oracle
```

## Reader Surface

The Reader has already moved most rendering and route IO into a vertical
`src/lib/reader/` cluster. The next quality target is continued reduction of
route-owned orchestration in `ReaderRouteController.svelte`.

```mermaid
flowchart TB
    ReaderRoute["/reader route"] --> ReaderController["ReaderRouteController.svelte"]
    ReaderController --> ReaderView["ReaderRouteControllerView.svelte"]
    ReaderView --> ReaderShell["ReaderShell.svelte"]
    ReaderShell --> DiscoveryView["ReaderDiscoveryView.svelte"]
    ReaderShell --> PassageView["ReaderPassageView.svelte"]
    ReaderShell --> ContextSidebar["ReaderContextSidebar.svelte"]
    ReaderShell --> SelectedWorkDesk["ReaderSelectedWorkDesk.svelte"]

    subgraph ReaderLoaders["Reader orchestration modules"]
        ReaderApiModule["reader-api.ts"]
        Workspace["reader-route-workspace.ts"]
        WorkspaceState["reader-route-workspace-state.ts"]
        ContentLoaders["reader-route-content-loaders.ts"]
        DiscoveryLoaders["reader-route-discovery-loaders.ts"]
        SelectedWord["reader-selected-word-controller.ts"]
        LoadingTimers["loading-timers.ts"]
    end

    subgraph ReaderPureHelpers["Reader pure helpers"]
        ReaderIndex["index.ts"]
        PageFormatting["page-formatting.ts"]
        PageRouting["page-routing.ts"]
        PageNavigation["page-navigation.ts"]
        PageAuthors["page-authors.ts"]
        IndexStats["index-stats.ts"]
        IndexStorage["index-storage.ts"]
        TextHelpers["text.ts"]
    end

    subgraph ReaderComponents["Reader component cluster"]
        DiscoveryChildren["Discovery, shelf, author, and search components"]
        PassageChildren["Leaf, page nav, source details, current division"]
        ApparatusChildren["Structure, word, oracle, and evidence panels"]
        ChromeChildren["Desk chrome, object cards, loading, and errors"]
    end

    ReaderController --> ReaderLoaders
    ReaderController --> ReaderPureHelpers
    ReaderView --> ReaderPureHelpers
    DiscoveryView --> DiscoveryChildren
    PassageView --> PassageChildren
    ContextSidebar --> ApparatusChildren
    SelectedWorkDesk --> ChromeChildren

    ContentLoaders --> ReaderApiModule
    DiscoveryLoaders --> ReaderApiModule
    SelectedWord --> ReaderApiModule
    Workspace --> WorkspaceState
    Workspace --> LoadingTimers
    ReaderApiModule --> ReaderApi["/api/reader"]
    SelectedWord --> EncounterApi["/api/encounter-briefing"]
    SelectedWord --> ReaderApi["/api/reader"]
```

## Lookup Request Flow

```mermaid
sequenceDiagram
    participant Browser as Browser
    participant Desk as "Word Desk route"
    participant Controller as "Desk controllers"
    participant Search as "Search API route"
    participant Adapter as "CLI adapter"
    participant Runtime as "langnet CLI"

    Browser->>Desk: Submit one word lookup
    Desk->>Controller: Parse route state and validate lookup
    Controller->>Search: Fetch encounter payload
    Search->>Adapter: Build CLI command
    Adapter->>Runtime: Run encounter JSON
    Runtime-->>Adapter: Return source-backed JSON
    Adapter-->>Search: Normalize web payload
    Search-->>Controller: Return lookup response
    Controller-->>Desk: Apply result, activity, and filters
    Desk-->>Browser: Render grouped dictionary evidence
```

## Reader Selected Word Flow

```mermaid
sequenceDiagram
    participant Browser as Browser
    participant Reader as "Reader route"
    participant SelectedWord as "Selected word controller"
    participant ReaderApi as "Reader API helpers"
    participant ReaderRoute as "Reader API route"
    participant Encounter as "Encounter briefing route"
    participant Runtime as "langnet CLI"

    Browser->>Reader: Select source token
    Reader->>SelectedWord: Build selected word request
    SelectedWord->>ReaderApi: Fetch reader word context
    ReaderApi->>ReaderRoute: Request local context
    ReaderRoute->>Runtime: Run reader context JSON
    Runtime-->>ReaderRoute: Return local passage evidence
    SelectedWord->>ReaderApi: Fetch encounter briefing
    ReaderApi->>Encounter: Request source-backed briefing
    Encounter->>Runtime: Run encounter JSON
    Runtime-->>Encounter: Return dictionary evidence
    Encounter-->>ReaderApi: Normalize response
    ReaderApi-->>SelectedWord: Return briefing payload
    SelectedWord-->>Reader: Apply word, oracle, and evidence state
    Reader-->>Browser: Render apparatus word panel
```

## Maintenance Rules

- Keep route files as orchestration boundaries. Components render, helpers
  transform, controllers coordinate side effects, and API routes adapt to CLI
  contracts.
- Add new Word Desk code under `webapp/src/lib/desk/` once it is not route-only
  state.
- Add new Reader code under `webapp/src/lib/reader/` unless it is a shared Orion
  primitive.
- Keep SvelteKit API routes thin. They should validate request parameters,
  invoke server-only adapters, and normalize output for the browser.
- Keep public docs and UI copy on the Project Orion name. Use `langnet-cli` only
  for internal runtime and developer-facing boundaries.
