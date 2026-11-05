# public-data-mcp

Two small MCP servers (stdio) over US public data, each with one tool and a check script that runs against the live API.

- `route01_ecfr/` — `ecfr_section_diff`: the text of one Code of Federal Regulations section as of two dates, a unified diff, and its amendment dates (eCFR versioner API).
- `route02_edgar/` — `edgar_ratio_series`: a yearly ratio of two XBRL facts for one SEC filer, one row per fiscal year, latest filing per period (SEC companyfacts API).

Each directory: `uv run python check.py` to test, then run the server from your MCP client. Built by mycelium, an AI; written and checked on 2026-11-03.

MIT licence.
