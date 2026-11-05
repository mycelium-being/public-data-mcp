import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
CACHE = os.environ.setdefault("EDGAR_CACHE_DIR", str(HERE / ".cache"))
sys.path.insert(0, str(HERE))
import server  # noqa: E402

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client, get_default_environment  # noqa: E402

FAILS = 0
ARGS = {"cik": 320193, "numerator_tag": "NetIncomeLoss",
        "denominator_tag": "RevenueFromContractWithCustomerExcludingAssessedTax"}


def check(name: str, ok: bool) -> None:
    global FAILS
    print(("PASS" if ok else "FAIL"), name)
    FAILS += 0 if ok else 1


def item(res: dict, end: str) -> dict:
    return next((i for i in res["series"] if i["fiscal_year_end"] == end), {})


async def over_stdio() -> dict:
    env = {**get_default_environment(), "EDGAR_CACHE_DIR": CACHE}
    params = StdioServerParameters(command="uv", args=["run", "--directory", str(HERE), "edgar-mcp"], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            check("stdio: exactly one tool named edgar_ratio_series", [t.name for t in tools] == ["edgar_ratio_series"])
            res = await s.call_tool("edgar_ratio_series", ARGS)
            if res.structuredContent is not None:
                return res.structuredContent.get("result", res.structuredContent)
            return json.loads(res.content[0].text)


a = server.edgar_ratio_series(**ARGS)
check("1 entity_name is Apple Inc.", a.get("entity_name") == "Apple Inc.")
check("2 years >= 10", a.get("years", 0) >= 10)
i19 = item(a, "2019-09-28")
check("3 FY2019 values and ratio", (i19.get("numerator"), i19.get("denominator"), i19.get("ratio")) == (55256000000, 260174000000, 0.212381))
i21 = item(a, "2021-09-25")
check("4 FY2021 values and ratio", (i21.get("numerator"), i21.get("denominator"), i21.get("ratio")) == (94680000000, 365817000000, 0.258818))
ends = [i["fiscal_year_end"] for i in a.get("series", [])]
check("5 strictly increasing, no repeats", all(x < y for x, y in zip(ends, ends[1:])))
before = server.FETCHES["count"]
server.edgar_ratio_series(**ARGS)
check("6 second identical call makes zero network requests (server.FETCHES counter)", server.FETCHES["count"] == before)
check("7 unknown tag returns error key", "error" in server.edgar_ratio_series(320193, "NoSuchTagAtAll", "Assets"))
b = asyncio.run(over_stdio())
j19 = item(b, "2019-09-28")
check("stdio: FY2019 item matches assertion 3", (j19.get("numerator"), j19.get("denominator"), j19.get("ratio")) == (55256000000, 260174000000, 0.212381))
print("network fetches by check process:", server.FETCHES["count"])
sys.exit(1 if FAILS else 0)
