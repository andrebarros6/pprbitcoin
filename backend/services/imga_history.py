"""
PPR performance-index fetcher for IM Gestao de Ativos (IMGA) and EuroBic.

Source: the chart API behind charts.imga.pt (apicharts.imga.pt), which IMGA
uses to render the performance charts on its own fund pages. It serves a real
daily observed series per fund, including funds managed for EuroBic.

Important difference from services/ppr_history.py: this endpoint returns a
performance INDEX rebased to 10,000 at the start of each series, not the unit
value (valor da unidade de participacao) in EUR. Returns, volatility, Sharpe,
Sortino and drawdown are all unaffected because they depend only on the ratio
between points -- but the stored numbers are not unit prices, and must not be
presented as such.

Fund ids come from funds/getData. They are verified against the names below on
every fetch, so a renumbering upstream fails loudly instead of silently
attaching one fund's history to another's name.
"""
import datetime as dt
import time
from decimal import Decimal
from typing import Dict, List

import httpx

API_BASE = "https://apicharts.imga.pt/api/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HISTORY_START = "1990-01-01"

# The series is rebased to 10,000, so plausible values sit far above a NAV.
MIN_PLAUSIBLE_INDEX = Decimal("100")
MAX_PLAUSIBLE_INDEX = Decimal("1000000")


class IMGADataError(RuntimeError):
    """Raised when real IMGA/EuroBic data cannot be retrieved or validated."""


# Only funds whose series the endpoint actually serves are listed. The CAT
# share classes (61602, 61604) duplicate the funds below with a shorter
# history starting 2021, and IMGA Crescimento (63100/63101) returns nothing,
# so none of them are seeded.
IMGA_FUNDS = [
    {
        "code": "61601",
        "designation": "IMGA Poupança PPR",
        "nome": "IMGA Poupança PPR",
        "gestor": "IM Gestão de Ativos",
        "categoria": "PPR Misto",
    },
    {
        "code": "61603",
        "designation": "IMGA Investimento PPR Ações",
        "nome": "IMGA Investimento PPR Ações",
        "gestor": "IM Gestão de Ativos",
        "categoria": "PPR Ações",
    },
    {
        "code": "60678",
        "designation": "EUROBIC PPR/OICVM Ciclo Vida -34",
        "nome": "EuroBic PPR Ciclo de Vida -34",
        "gestor": "IM Gestão de Ativos",
        "categoria": "PPR Ações",
    },
    {
        "code": "60679",
        "designation": "EUROBIC PPR/OICVM Ciclo Vida -35-44",
        "nome": "EuroBic PPR Ciclo de Vida 35-44",
        "gestor": "IM Gestão de Ativos",
        "categoria": "PPR Misto",
    },
    {
        "code": "60681",
        "designation": "EUROBIC PPR/OICVM Ciclo Vida -45-54",
        "nome": "EuroBic PPR Ciclo de Vida 45-54",
        "gestor": "IM Gestão de Ativos",
        "categoria": "PPR Misto",
    },
    {
        "code": "60682",
        "designation": "EUROBIC PPR/OICVM Ciclo Vida +55",
        "nome": "EuroBic PPR Ciclo de Vida +55",
        "gestor": "IM Gestão de Ativos",
        "categoria": "PPR Moderado",
    },
]


def _client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=90,
        follow_redirects=True,
    )


def _post(client: httpx.Client, path: str, payload: dict, retries: int = 4):
    last_error = None
    for attempt in range(retries):
        try:
            response = client.post(API_BASE + path, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise IMGADataError(f"{path} failed after {retries} attempts: {last_error}")


def fetch_fund_ids(client: httpx.Client) -> Dict[str, str]:
    """Map fund id -> designation, used to verify the hardcoded ids."""
    payload = _post(client, "funds/getData", {})
    return {
        str(f["portfolioID"]): str(f.get("designation", "")).strip()
        for f in payload.get("listFunds", [])
    }


def fetch_fund_series(
    client: httpx.Client, fund: dict, start: str = HISTORY_START
) -> Dict[dt.date, Decimal]:
    """Fetch one fund's daily performance index."""
    # `code` must be a string; the API rejects an integer with
    # "O valor nao e uma sequencia".
    payload = _post(
        client,
        "performances/getData",
        {
            "startDate": start,
            "endDate": dt.date.today().isoformat(),
            "code": str(fund["code"]),
        },
    )

    rows = payload.get("performance") or []
    series: Dict[dt.date, Decimal] = {}
    for row in rows:
        raw_date = row.get("date")
        raw_value = row.get("value")
        if raw_date is None or raw_value is None:
            continue
        try:
            day = dt.date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            continue
        value = Decimal(str(raw_value))
        if value > 0:
            series[day] = value

    validate_series(fund["nome"], series)
    return series


def validate_series(
    nome: str, series: Dict[dt.date, Decimal], min_days: int = 500
) -> None:
    """
    Guard against seeding implausible or stale data.

    Mirrors the checks in services/ppr_history.py, with bounds appropriate to
    a series rebased to 10,000 rather than a unit value.
    """
    if len(series) < min_days:
        raise IMGADataError(
            f"{nome}: only {len(series)} observations, expected >= {min_days}."
        )

    bad = [
        (day, value)
        for day, value in series.items()
        if not (MIN_PLAUSIBLE_INDEX <= value <= MAX_PLAUSIBLE_INDEX)
    ]
    if bad:
        raise IMGADataError(f"{nome}: implausible index values, e.g. {bad[:3]}")

    newest = max(series)
    staleness = (dt.date.today() - newest).days
    if staleness > 10:
        raise IMGADataError(
            f"{nome}: newest point is {newest} ({staleness} days old). Stale."
        )

    days = sorted(series)
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days > 10:
            continue  # tolerate genuine reporting gaps
        change = abs(series[curr] / series[prev] - 1)
        if change > Decimal("0.35"):
            raise IMGADataError(
                f"{nome}: implausible {change:.0%} move {prev} -> {curr}."
            )


def fetch_all_funds(start: str = HISTORY_START) -> List[dict]:
    """Fetch every configured IMGA/EuroBic PPR fund with its daily series."""
    results = []
    with _client() as client:
        known = fetch_fund_ids(client)

        for fund in IMGA_FUNDS:
            actual = known.get(fund["code"])
            if actual is None:
                raise IMGADataError(
                    f"{fund['nome']}: fund id {fund['code']} no longer listed "
                    f"by the source."
                )
            if actual.casefold() != fund["designation"].casefold():
                raise IMGADataError(
                    f"{fund['nome']}: id {fund['code']} is now "
                    f"{actual!r}, expected {fund['designation']!r}. Refusing "
                    f"to attach mismatched history."
                )

            series = fetch_fund_series(client, fund, start=start)
            results.append({**fund, "nav": series})
            print(
                f"  [OK] {fund['nome']}: {len(series)} daily points "
                f"({min(series)} -> {max(series)})"
            )
    return results
