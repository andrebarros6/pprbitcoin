"""
PPR performance-index fetcher for Casa de Investimentos.

Source: the JSON API behind casadeinvestimentos.pt's fund charts, which reads
an Excel workbook and returns it as rows. It needs no browser, no key and no
session, so unlike services/investing_history.py this one can run unattended.

Like services/imga_history.py, the series is an INDEX rebased to 100 at
inception, not a unit value in EUR. Returns, volatility, Sharpe, Sortino and
drawdown are unaffected -- they depend only on ratios between points -- but
the stored numbers are not unit prices and must not be presented as such.

Naming: the manager markets this as "Casa Global Value PPR/OICVM Founders",
while the CMVM registers it as "Save & Grow PPR/OICVM" (NUM_FUN 1637). The
identity was established by matching returns, not names -- measured to
2025-12-30 the series gives 1y 5.46%, matching CMVM's 5.46% for the class
whose TEC is 1.41%.

Each worksheet returns three columns: an Excel serial date, the fund, and a
benchmark. Column C is NOT the fund: its returns miss CMVM by ~2.15pp while
column B matches to 0.13pp.
"""
import datetime as dt
import time
from decimal import Decimal
from typing import Dict, List

import httpx

API_URL = "https://casa-de-investimentos-api.vercel.app/api/get-excel-data"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# The workbook is queried by a fixed cell range; trailing empty rows are
# filtered out rather than the range being guessed per fund.
CELL_RANGE = "B5:D50000"

# Excel serial day 1 is 1900-01-01, but Excel wrongly treats 1900 as a leap
# year, so the usable epoch is 1899-12-30.
EXCEL_EPOCH = dt.date(1899, 12, 30)

# The series is rebased to 100, so plausible values sit well above zero but
# far below a raw index like IMGA's 10,000 base.
MIN_PLAUSIBLE_INDEX = Decimal("1")
MAX_PLAUSIBLE_INDEX = Decimal("100000")


class CasaDataError(RuntimeError):
    """Raised when Casa de Investimentos data cannot be retrieved or validated."""


CASA_FUNDS = [
    {
        "worksheet": "grafico_founders",
        "nome": "Casa Global Value PPR Founders",
        "gestor": "Casa de Investimentos",
        "categoria": "PPR Ações",
        # Confirmed against CMVM at 2025-12-30: 1y 5.46 vs 5.46,
        # 3y 20.25 vs 20.29, mean deviation 0.13pp.
        "cmvm_name": "SAVE & GROW PPR/OICVM",
    },
]


def _excel_date(serial) -> dt.date:
    return EXCEL_EPOCH + dt.timedelta(days=int(float(serial)))


def fetch_fund_series(fund: dict, retries: int = 4) -> Dict[dt.date, Decimal]:
    """Fetch one fund's daily index series."""
    last_error = None
    for attempt in range(retries):
        try:
            response = httpx.get(
                API_URL,
                params={"worksheet": fund["worksheet"], "range": CELL_RANGE},
                headers={"User-Agent": USER_AGENT},
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt == retries - 1:
                raise CasaDataError(
                    f"{fund['nome']}: request failed: {last_error}"
                ) from exc
            time.sleep(2 * (attempt + 1))

    if isinstance(payload, dict):
        # The upstream Excel service reports errors as a JSON object.
        raise CasaDataError(
            f"{fund['nome']}: worksheet '{fund['worksheet']}' not available: "
            f"{str(payload)[:200]}"
        )

    series: Dict[dt.date, Decimal] = {}
    for row in payload:
        # The fixed cell range pads the response with empty trailing rows.
        if not row or len(row) < 2 or str(row[0]).strip() in ("", "None"):
            continue
        try:
            day = _excel_date(row[0])
            value = Decimal(str(row[1]))
        except (ValueError, TypeError, ArithmeticError):
            continue
        if value > 0:
            series[day] = value

    validate_series(fund["nome"], series)
    return series


def validate_series(
    nome: str, series: Dict[dt.date, Decimal], min_days: int = 500
) -> None:
    """Guard against seeding implausible or stale data."""
    if len(series) < min_days:
        raise CasaDataError(
            f"{nome}: only {len(series)} observations, expected >= {min_days}."
        )

    bad = [
        (day, value)
        for day, value in series.items()
        if not (MIN_PLAUSIBLE_INDEX <= value <= MAX_PLAUSIBLE_INDEX)
    ]
    if bad:
        raise CasaDataError(f"{nome}: implausible index values, e.g. {bad[:3]}")

    newest = max(series)
    staleness = (dt.date.today() - newest).days
    if staleness > 10:
        raise CasaDataError(
            f"{nome}: newest point is {newest} ({staleness} days old). Source is stale."
        )

    days = sorted(series)
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days > 10:
            continue  # tolerate genuine reporting gaps
        change = abs(series[curr] / series[prev] - 1)
        if change > Decimal("0.35"):
            raise CasaDataError(
                f"{nome}: implausible {change:.0%} move {prev} -> {curr}. "
                f"Possible split or parse error."
            )


def fetch_all_funds() -> List[dict]:
    """Fetch every configured Casa de Investimentos fund."""
    results = []
    for fund in CASA_FUNDS:
        series = fetch_fund_series(fund)
        results.append({**fund, "nav": series})
        print(
            f"  [OK] {fund['nome']}: {len(series)} daily points "
            f"({min(series)} -> {max(series)})"
        )
    return results
