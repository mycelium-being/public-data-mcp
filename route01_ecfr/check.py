import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
CACHE = os.environ.setdefault("ECFR_CACHE_DIR", str(HERE / ".cache"))
sys.path.insert(0, str(HERE))
import server  # noqa: E402

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client, get_default_environment  # noqa: E402

FAILS = 0


def check(name: str, ok: bool) -> None:
    global FAILS
    print(("PASS" if ok else "FAIL"), name)
    FAILS += 0 if ok else 1


async def over_stdio() -> dict:
    env = {**get_default_environment(), "ECFR_CACHE_DIR": CACHE}
    params = StdioServerParameters(command="uv", args=["run", "--directory", str(HERE), "ecfr-mcp"], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            check("stdio: exactly one tool named ecfr_section_diff", [t.name for t in tools] == ["ecfr_section_diff"])
            res = await s.call_tool("ecfr_section_diff", {"title": 29, "section": "541.600", "date_a": "2019-12-01", "date_b": "2020-02-01"})
            if res.structuredContent is not None:
                return res.structuredContent.get("result", res.structuredContent)
            return json.loads(res.content[0].text)


a = server.ecfr_section_diff(29, "541.600", "2019-12-01", "2020-02-01")
print("paragraphs text_a:", len(a["text_a"].split("\n")), "text_b:", len(a["text_b"].split("\n")), "diff lines:", len(a["diff"].split("\n")))
check("direct: 2019-12-01 vs 2020-02-01 diff non-empty", bool(a["diff"]))
check("direct: text_b contains 684", "684" in a["text_b"])
same = server.ecfr_section_diff(29, "541.600", "2020-02-01", "2020-02-01")
check("direct: same date both sides gives empty diff", same["diff"] == "")
c = server.ecfr_section_diff(29, "541.600", "2019-12-01", "2024-01-01")
check("direct: 2019-12-01 vs 2024-01-01 diff non-empty", bool(c["diff"]))
try:
    server.ecfr_section_diff(29, "541.600", "1990-01-01", "2020-02-01")
    check("direct: date before first version raises ToolError", False)
except server.ToolError as e:
    print("   error message:", str(e)[:200])
    check("direct: date before first version raises ToolError", True)
b = asyncio.run(over_stdio())
check("stdio: diff non-empty", bool(b["diff"]))
check("stdio: diff equals direct diff", b["diff"] == a["diff"])
print("fetches by check process (cache misses):", server.FETCHES["count"])
sys.exit(1 if FAILS else 0)
