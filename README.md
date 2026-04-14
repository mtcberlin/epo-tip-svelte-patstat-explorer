# PATSTAT Explorer

Interactive patent analysis on PATSTAT, built for the EPO Technology Intelligence Platform (TIP) JupyterHub and maintained with the EPO Academy and the PATLIB TIP Working Group.

## Quick start

The only file you need is [`PATSTAT_Explorer.ipynb`](PATSTAT_Explorer.ipynb).

1. Download it from this repo (or *File → Save Link As…* on the [raw link](https://raw.githubusercontent.com/mtcberlin/epo-tip-svelte-patstat-explorer/main/PATSTAT_Explorer.ipynb)).
2. Upload it to your home directory on the [EPO Technology Intelligence Platform](https://tip.epo.org/).
3. Open it, click into the code cell, and run it (play button, Shift+Enter, or Menu → Run → Run selected cell).

The notebook installs and starts everything for you. A clickable link appears when it's ready. **First run takes 1–2 minutes.**

The notebook starts three local services (a schema-discovery helper, a Python API, and the web app) on your TIP JupyterHub environment. You never touch them directly.

## What it does

PATSTAT Explorer has **two ways to start an analysis** and **two standalone tools**.

### Start an analysis

- **Applicant Search** — find an organisation by name. PATSTAT stores many name variants for the same company (`SIEMENS AG`, `SIEMENS LTD`, `SIEMENS CORP`). The app auto-suggests which variants belong together and lets you group them as a single entity before you dive in.
- **Technology Search** — type a CPC code (`H01M`) or a plain-English description (`battery`) and see the top applicants filing in that technology area. Click an applicant to drop into the same deep-dive.

### Deep-dive (opens when you pick an applicant)

- **Overview** — filing trend over time, top jurisdictions, top CPC technology fields.
- **Network** — who files patents together with this organisation.
- **Citations** — which technologies the organisation cites and which technologies cite back.
- **CPC Map** — a heatmap of how the portfolio spreads across CPC sections, revealing technology overlaps.

### Standalone tools

- **Country Comparison** — chart patent filings for a set of countries (DE, US, CN, JP, KR, …), optionally filtered to a technology.
- **AI Query** — if the built-in views don't answer your question, ask in plain English and Claude writes the SQL for you. Bring your own Anthropic API key.

## Credits

- **Concept** — [Arne Krueger](https://www.linkedin.com/in/herrkrueger/)
- **Architecture** — [Matze Schmidbauer](https://www.linkedin.com/in/matzeschmidbauer/)
- **Inspiration** — [Chris Toft](https://www.linkedin.com/in/chris-toft-/)

Created for the EPO Academy and the PATLIB TIP Working Group, 2025–2026.
© European Patent Organisation and mtc.berlin — see [LICENSE.txt](LICENSE.txt).
</content>
</invoke>