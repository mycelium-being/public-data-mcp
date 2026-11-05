"""MCP server with one tool: edgar_ratio_series, over the SEC company-facts API."""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

BASE = "https://data.sec.gov/api/xbrl/companyfacts"
HEADERS = {"User-Agent": "mycelium (mycelium.self@proton.me)", "Accept-Encoding": "gzip"}
CACHE = Path(os.environ.get("EDGAR_CACHE_DIR") or Path(__file__).parent / ".cache")
FETCHES = {"count": 0}
NOTE = ("Rows with fp FY and form 10-K*; duration rows only if 350-380 days long; "
        "latest filed row per period end; a year needs both tags; year is the period end, not fy.")

mcp = FastMCP("edgar")


def _get(url: str) -> tuple[int, str]:
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if path.exists():
        return 200, path.read_text()
    last = (0, "request failed")
    for _ in range(2):
        try:
            r = httpx.get(url, headers=HEADERS, timeout=60, follow_redirects=True)
        except httpx.HTTPError as e:
            last = (0, f"request failed: {e}")
            continue
        FETCHES["count"] += 1
        if r.status_code == 200:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(r.text)
            return 200, r.text
        last = (r.status_code, r.text[:300])
        if r.status_code < 500:
            break
    return last


def _kept(tag: str, rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        if r.get("fp") != "FY" or not str(r.get("form", "")).startswith("10-K"):
            continue
        if r.get("start"):
            days = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
            if not 350 <= days <= 380:
                continue
        cur = out.get(r["end"])
        if cur is None or r["filed"] > cur["filed"]:
            out[r["end"]] = r
    return out


@mcp.tool()
def edgar_ratio_series(cik: int, numerator_tag: str, denominator_tag: str) -> dict:
    """Yearly ratio of two us-gaap USD XBRL tags for one SEC filer (CIK), with the raw values per fiscal year."""
    status, body = _get(f"{BASE}/CIK{int(cik):010d}.json")
    if status != 200:
        return {"error": f"SEC answered {status}: {body}"}
    data = json.loads(body)
    facts = data.get("facts", {}).get("us-gaap", {})
    units = {}
    for tag in (numerator_tag, denominator_tag):
        if tag not in facts:
            return {"error": f"unknown us-gaap tag: {tag}"}
        units[tag] = facts[tag].get("units", {})
        if "USD" not in units[tag]:
            return {"error": f"tag {tag} has no USD unit; units present: {sorted(units[tag])}"}
    num = _kept(numerator_tag, units[numerator_tag]["USD"])
    den = _kept(denominator_tag, units[denominator_tag]["USD"])
    series = []
    for end in sorted(num.keys() & den.keys()):
        n, d = num[end], den[end]
        series.append({
            "fiscal_year_end": end, "numerator": n["val"], "denominator": d["val"],
            "ratio": round(n["val"] / d["val"], 6) if d["val"] else None,
            "numerator_filed": n["filed"], "denominator_filed": d["filed"],
        })
    return {
        "cik": int(cik), "entity_name": data.get("entityName"),
        "numerator_tag": numerator_tag, "denominator_tag": denominator_tag,
        "unit": "USD", "series": series, "years": len(series), "note": NOTE,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
