"""
CMVM PPR reference data.

The CMVM (the Portuguese securities regulator) publishes a PPR comparator at
https://investidor.cmvm.pt/PInvestidor/Comparator. Its underlying data action
returns the full register of PPR funds -- 167 at the time of writing -- with
annualised returns at YTD/1/2/3/5/10 years, the risk class, and the Taxa de
Encargos Correntes (TEC, the ongoing charges figure).

Two things make this the strongest verification source available:

  - It is the regulator's own register, independent of both the fund manager
    (which supplies our NAV series) and APFIPP (the industry association).
  - It publishes a 10-year horizon. APFIPP stops at 5 years, so CMVM is the
    only source that can check the deep end of a long NAV series.

Unlike Investing.com, this endpoint works from a plain server-side request --
no browser required -- so it can run in CI and in the scheduled refresh.

Figures are as of the end of the preceding calendar year (verified: the
2026 dataset reproduces our NAV-implied returns exactly when measured as of
2025-12-31). Comparing against a different as-of date produces large
spurious differences on short horizons, so callers must align dates.
"""
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional

import httpx

BASE = "https://investidor.cmvm.pt/PInvestidor/"
URL = BASE + "screenservices/PInvestidor/Comparator/PPRList/DataActionGetPPRs"

# The OutSystems data action needs a full screen-state envelope. It is stored
# alongside this module rather than inlined; refresh it from the browser's
# network tab if CMVM ships a new module version.
REQUEST_TEMPLATE = Path(__file__).parent.parent / "data" / "cmvm_request.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def reference_as_of(today: Optional[dt.date] = None) -> dt.date:
    """CMVM figures are published as at the end of the previous calendar year."""
    today = today or dt.date.today()
    return dt.date(today.year - 1, 12, 31)


class CMVMDataError(RuntimeError):
    """Raised when the CMVM register cannot be retrieved."""


def fetch_ppr_register(max_records: int = 500) -> List[dict]:
    """
    Fetch the full CMVM PPR register.

    Returns the raw fund records. Raises CMVMDataError rather than returning
    partial data, so a verification run fails loudly instead of silently
    checking against nothing.
    """
    try:
        body = json.loads(REQUEST_TEMPLATE.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CMVMDataError(f"Cannot read {REQUEST_TEMPLATE}: {exc}") from exc

    body["screenData"]["variables"]["MaxRecords"] = max_records
    body["screenData"]["variables"]["StartIndex"] = 0

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json",
        "Origin": "https://investidor.cmvm.pt",
        "Referer": BASE + "PPRList",
        "X-CSRFToken": "",
    }

    try:
        response = httpx.post(URL, json=body, headers=headers, timeout=90)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise CMVMDataError(f"CMVM request failed: {exc}") from exc

    if "data" not in payload:
        # A stale moduleVersion in the template is the usual cause.
        raise CMVMDataError(
            "Unexpected CMVM response shape; the request template may be "
            f"out of date: {json.dumps(payload)[:300]}"
        )

    funds = payload["data"]["PPRList"]["List"]
    if not funds:
        raise CMVMDataError("CMVM returned an empty register.")
    return funds


def _clean(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def returns_by_fund(funds: List[dict]) -> Dict[str, Dict[int, float]]:
    """
    Map upper-cased fund name -> {horizon_years: annualised return %}.

    Records flagged HAS_REND_* false carry 0.0 placeholders; those are dropped
    so a missing figure is never mistaken for a real 0% return.
    """
    result: Dict[str, Dict[int, float]] = {}
    for fund in funds:
        horizons = {}
        for years, key in [(1, "1Y"), (2, "2Y"), (3, "3Y"), (5, "5Y"), (10, "10Y")]:
            if not fund.get(f"HAS_REND_{key}"):
                continue
            value = _clean(fund.get(f"REND_{key}"))
            if value is not None:
                horizons[years] = value
        if horizons:
            result[fund["NOM_FUN"].strip().upper()] = horizons
    return result


def tec_by_fund(funds: List[dict]) -> Dict[str, float]:
    """
    Map fund name -> Taxa de Encargos Correntes (%).

    This is the ongoing charges figure. Our NAV series are already net of
    fees, so the TEC is displayed for comparison, not applied to returns.
    """
    result = {}
    for fund in funds:
        if not fund.get("HAS_TAXA_TEC"):
            continue
        value = _clean(fund.get("TAXA_TEC"))
        if value is not None:
            result[fund["NOM_FUN"].strip().upper()] = value
    return result
