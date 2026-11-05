"""MCP server with one tool: ecfr_section_diff, over the eCFR versioner API."""
import difflib
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

BASE = "https://www.ecfr.gov/api/versioner/v1"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
CACHE = os.environ.get("ECFR_CACHE_DIR")
FETCHES = {"count": 0}

mcp = FastMCP("ecfr")


def _get(url: str, key: str) -> str:
    path = None
    if CACHE:
        path = Path(CACHE) / (hashlib.sha1(key.encode()).hexdigest() + ".txt")
        if path.exists():
            return path.read_text()
    last = None
    for _ in range(2):
        try:
            r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        except httpx.HTTPError as e:
            last = f"request failed: {e}"
            continue
        FETCHES["count"] += 1
        if r.status_code == 200:
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(r.text)
            return r.text
        last = f"eCFR answered {r.status_code}: {r.text[:300]}"
        if r.status_code < 500:
            break
    raise ToolError(last or "eCFR request failed")


def _text(xml: str) -> list[str]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ToolError(f"eCFR returned unparseable XML: {e}")
    clean = lambda el: re.sub(r"\s+", " ", "".join(el.itertext())).strip()
    lines = []
    head = root.find(".//HEAD")
    if head is not None:
        lines.append(clean(head))
    lines += [t for p in root.iter("P") if (t := clean(p))]
    if not lines:
        raise ToolError("eCFR returned no text for this section and date")
    return lines


def _versions(title: int, section: str) -> list[str]:
    part = section.split(".")[0]
    url = f"{BASE}/versions/title-{title}.json?part={part}&section={section}"
    import json
    data = json.loads(_get(url, f"v|{title}|{section}"))
    return [v["amendment_date"] for v in data.get("content_versions", []) if v.get("amendment_date")]


def _section(title: int, section: str, date: str) -> list[str]:
    url = f"{BASE}/full/{date}/title-{title}.xml?section={section}"
    return _text(_get(url, f"f|{title}|{section}|{date}"))


@mcp.tool()
def ecfr_section_diff(title: int, section: str, date_a: str, date_b: str) -> dict:
    """Return the text of one CFR section as of two dates (YYYY-MM-DD) and a unified diff between them."""
    a = _section(title, section, date_a)
    b = _section(title, section, date_b)
    diff = "\n".join(difflib.unified_diff(a, b, fromfile=date_a, tofile=date_b, lineterm=""))
    return {
        "title": title, "section": section, "date_a": date_a, "date_b": date_b,
        "text_a": "\n".join(a), "text_b": "\n".join(b), "diff": diff,
        "versions": _versions(title, section),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
