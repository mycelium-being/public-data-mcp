# ecfr-mcp

A local MCP server (stdio) with one tool, `ecfr_section_diff(title, section, date_a, date_b)`. It returns the plain text of one CFR section as of two dates, a unified diff between them, and the list of amendment dates for that section.

Endpoints (eCFR versioner API):
- `GET https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title}.xml?section={section}`
- `GET https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json?part={part}&section={section}`

Errors from the API (bad section, date before the first version) are raised as tool errors carrying the API's message.

Start: `uv run ecfr-mcp`

Check: `uv run python check.py` (set `ECFR_CACHE_DIR` to cache fetches on disk; prints PASS/FAIL per assertion, exits non-zero on any FAIL).

Note: requires `mcp<2` (FastMCP API).
