# PATSTAT Explorer

**mtc.berlin · EPO TIP**

Patent analysis and visualization platform for the EPO PATSTAT database on Google BigQuery. Built for the EPO Technology and Innovation Programme (TIP) JupyterHub environment.

## Quick Start (TIP)

The only file you need is [`PATSTAT_Explorer.ipynb`](PATSTAT_Explorer.ipynb).

1. Download it from this repo (or: *File → Save Link As…* on the [raw link](https://raw.githubusercontent.com/mtcberlin/epo-tip-svelte-patstat-explorer/main/PATSTAT_Explorer.ipynb))
2. Upload it to your TIP JupyterHub home directory
3. Open it and run the single cell

That's it. The notebook clones this repository into `~/patstat_svelte`, installs all dependencies (Node.js, MCP server, Python packages), builds the app, and starts three services. A clickable link to the PATSTAT Explorer appears when everything is ready.

**First run (~1–2 min):** clones this repo, installs dependencies, builds the app, starts all services.
**Subsequent runs (~10s):** pulls latest changes via `git pull`, starts services. The build step is skipped if no source files changed.

To stop: run `stop()` in the notebook or restart the kernel.

## What It Does

PATSTAT Explorer provides interactive views for patent data analysis — applicant trends, co-filing networks, citation flows, technology classifications, and an AI-powered query interface.

### Views

| Route | Feature | Description |
|---|---|---|
| `/` | Home | Overview, connection check, navigation |
| `/search` | Applicant Search | Find applicants by name, consolidate name variants (auto-suggest), preview trends |
| `/applicant` | Applicant Analysis | Filing trends, top jurisdictions, CPC technology fields (tabs) |
| `/text-search` | Text Search | Full-text search in patent titles and abstracts (English) |
| `/technology` | Technology Search | Browse by CPC code — filing trends and top applicants |
| `/countries` | Country Comparison | Compare filing trends across multiple countries with optional CPC filter |
| `/network` | Co-Applicant Network | Interactive D3 force-directed graph of co-filing partners |
| `/citations` | Citation Flow | D3 Sankey diagram — forward/backward citation analysis by technology field |
| `/co-occurrence` | CPC Co-Occurrence | 9×9 heatmap showing how often CPC sections appear together |
| `/query` | AI Query | Natural language → SQL via MCP tools, or direct SQL editor |

### AI Query Interface

The AI Query page (`/query`) supports two modes:

- **Natural Language:** Ask questions like "Top 10 applicants in solid-state battery patents since 2015". Claude discovers the PATSTAT schema via MCP tools (`list_tables`, `get_table_schema`, `search_tables`, `get_table_samples`, `execute_query`), builds SQL, executes it, and returns results. All intermediate steps are streamed live to the UI.
- **SQL Mode:** Write and execute BigQuery SQL directly.

BYOK (Bring Your Own Key): The Anthropic API key is entered once via the Settings dialog and stored locally in `~/.patent-navigator/config.json`. The MCP server does not require an API key.

### Patent Detail Sheet

Clicking any patent row (in Text Search, AI Query, or any table with `appln_id`) opens a side panel showing:
- Title, abstract, basic metadata (authority, filing date, kind, granted status)
- Applicants with country badges and links to applicant analysis
- CPC codes linking to [Patent Classification Explorer](https://patentclassificationexplorer.com)
- Espacenet link

### Name Consolidation

PATSTAT contains many name variants for the same organization (SIEMENS AG, SIEMENS LTD, SIEMENS CORP, etc.). The search page provides:
- Auto-suggest grouping by core name (strips legal suffixes like AG, GmbH, Inc, Ltd, SA, NV)
- Multi-select with custom parent label
- All consolidated names are carried through to every deep-dive view via URL parameters (`names=A|||B|||C&label=Group`)
- Collapsible display on all pages showing which names are included

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Browser                                             │
│  SvelteKit 5 · Tailwind CSS 4 · shadcn-svelte       │
│  D3.js (Force Graph, Sankey) · LayerChart            │
└──────────────┬───────────────────────────────────────┘
               │ HTTP
┌──────────────▼───────────────────────────────────────┐
│  SvelteKit Node.js Server (Port 52080)               │
│  Proxies API requests, serves static assets          │
└──────────────┬───────────────────────────────────────┘
               │ HTTP
┌──────────────▼───────────────────────────────────────┐
│  Python Sidecar — FastAPI (Port 52081)               │
│  SQL validation, patent detail, co-occurrence,       │
│  settings, agentic NL-to-SQL loop (SSE streaming)    │
└──────┬───────────────────────────┬───────────────────┘
       │                           │
       │ BigQuery                  │ MCP (Streamable HTTP)
       ▼                           ▼
┌──────────────┐    ┌──────────────────────────────────┐
│  PATSTAT     │    │  mtc.berlin PATSTAT MCP          │
│  (BigQuery)  │    │  (Port 8082)                     │
│              │    │  Schema discovery & query tools   │
└──────────────┘    └──────────────────────────────────┘
```

### Process Management

`launch.py` orchestrates the full startup:

1. **MCP install** — `pip install --user` from [mtcberlin/mtc-patstat-mcp-lite](https://github.com/mtcberlin/mtc-patstat-mcp-lite) (idempotent)
2. **npm install** — only if `node_modules` doesn't exist
3. **npm run build** — only if source files changed since last build
4. **Start MCP server** (Port 8082) — schema discovery and query execution tools
5. **Start Sidecar** (Port 52081) — FastAPI, connects to MCP and BigQuery
6. **Start App** (Port 52080) — SvelteKit production server

All processes are managed in-memory. `stop()` terminates everything cleanly.

### Stateless Context via URL

There is no app-level state store. All analysis context is encoded in URL search parameters:

```
/applicant?names=SIEMENS%20AG|||SIEMENS%20LTD&label=Siemens&cpc=H01M&from=2015&to=2024
```

`src/lib/context.ts` provides `parseContext()`, `contextToParams()`, `nameWhereClause()`, and `contextLink()` for consistent handling across all views.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | SvelteKit 2 · Svelte 5 (runes) |
| Styling | Tailwind CSS 4 · shadcn-svelte · Bits UI |
| Charts | LayerChart (bar/line) · D3.js (force graph, sankey, heatmap SVG) |
| Icons | Lucide Svelte |
| Backend | FastAPI (Python) · Node.js adapter (SvelteKit) |
| Data | EPO PATSTAT on Google BigQuery via `PatstatClient` |
| AI | Anthropic Claude API (BYOK) · MCP (Model Context Protocol) |
| Testing | Vitest + @testing-library/svelte (frontend) · pytest (backend) |
| Language | TypeScript (strict) · Python 3.12 |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | BigQuery connection check |
| `POST` | `/api/query` | Execute validated SQL (SELECT only, 10KB limit) |
| `GET` | `/api/patent/{appln_id}` | Patent details (basic info, applicants, CPC codes) |
| `POST` | `/api/nl-to-sql` | Agentic NL-to-SQL via MCP tools (SSE stream) |
| `GET/POST` | `/api/settings` | API key and model configuration |
| `POST` | `/api/co-occurrence` | CPC section co-occurrence matrix |

## Project Structure

```
├── launch.py                    # Bootstrap & process management
├── sidecar.py                   # FastAPI backend (BigQuery + MCP + Claude)
├── package.json                 # Node.js dependencies & scripts
├── svelte.config.js             # SvelteKit configuration (node adapter)
├── vite.config.ts               # Vite + Vitest configuration
├── src/
│   ├── app.css                  # Tailwind theme (MTC branding, oklch tokens)
│   ├── lib/
│   │   ├── context.ts           # URL-based analysis context
│   │   ├── patstat.ts           # Sidecar API client
│   │   ├── csv.ts               # Client-side CSV export
│   │   ├── utils.ts             # cn() utility
│   │   └── components/
│   │       ├── consolidated-names.svelte
│   │       ├── patent-detail-sheet.svelte
│   │       └── ui/              # shadcn-svelte components
│   │           ├── badge/       ├── button/      ├── card/
│   │           ├── checkbox/    ├── collapsible/  ├── dialog/
│   │           ├── input/       ├── separator/    ├── sheet/
│   │           ├── table/       ├── tabs/         └── textarea/
│   └── routes/
│       ├── +layout.svelte       # Navigation header
│       ├── +page.svelte         # Home
│       ├── search/              # Applicant search + consolidation
│       ├── applicant/           # Applicant analysis (trends, jurisdictions, CPC)
│       ├── text-search/         # Full-text patent search
│       ├── technology/          # CPC code browser
│       ├── countries/           # Country comparison
│       ├── network/             # Co-applicant force graph
│       ├── citations/           # Citation Sankey diagram
│       ├── co-occurrence/       # CPC heatmap
│       ├── query/               # AI Query Interface
│       └── api/                 # Server-side API routes
│           ├── health/
│           ├── query/
│           ├── patent/[appln_id]/
│           ├── nl-to-sql/
│           ├── settings/
│           └── co-occurrence/
├── tests/                       # Python tests (pytest)
│   ├── test_sidecar.py          # Health, query, settings, patent detail, NL-to-SQL
│   ├── test_mcp_agent.py        # Tool conversion, agentic loop, max iterations
│   └── test_sql_extract.py      # SQL extraction from markdown/text
└── static/
    ├── logo.svg
    ├── logo.png
    └── robots.txt
```

## Testing

```bash
# Frontend (Vitest — 59 tests)
npm test

# Backend (pytest — 40 tests)
python -m pytest tests/

# Both
npm test && python -m pytest tests/
```

Tests cover: URL context parsing, CSV export, API client, SQL validation, patent detail endpoint, settings CRUD, NL-to-SQL SSE streaming, MCP tool conversion, agentic loop behavior, SQL extraction from markdown/text, max iterations safeguard.

## Development

```bash
npm run dev          # Vite dev server with HMR
npm run check        # TypeScript/Svelte type checking
npm run test:watch   # Vitest in watch mode
```

The sidecar must be running separately for the app to work:

```bash
python sidecar.py                    # Port 52081
patstat-mcp-lite --http --port 8082  # MCP server (optional, for AI Query)
```

## Deployment

The app is designed for EPO TIP JupyterHub. It uses relative asset paths (`paths.relative: true` in `svelte.config.js`) to work behind the JupyterHub proxy at any base path.

Production builds are generated by `npm run build` into the `build/` directory and served with `node build/`.

## License

Internal — mtc.berlin · EPO TIP
