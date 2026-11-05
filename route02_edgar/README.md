# edgar-mcp

A stdio MCP server with one tool, `edgar_ratio_series(cik, numerator_tag, denominator_tag)`.

It fetches one SEC company-facts file (data.sec.gov) per filer and returns, per fiscal year, the ratio of two us-gaap USD tags with both raw values and filing dates.

Selection rule: form 10-K*, fp FY; duration facts must span 350-380 days; the latest filing wins per period end; the year is labelled by the period end, not by `fy`.

Run: `uv run edgar-mcp`. Cache: `EDGAR_CACHE_DIR` (default `.cache` beside server.py). Requests carry one fixed User-Agent, as the SEC's fair-access policy asks.

Check: `uv run python check.py`.
