"""
PPR daily NAV (valor da unidade de participação) fetcher.

Source: Optimize Investment Partners publish the full daily NAV series for
each of their PPR funds through the chart endpoint on their public fund
pages. That gives a real observed daily series -- not interpolation between
annual return figures -- so volatility, Sharpe, Sortino and drawdown computed
from it are genuine.

Why not the alternatives (see DATA_SOURCES.md for the full survey):
  - Investing.com blocks scripted requests (HTTP 403, Cloudflare). A visible
    non-headless browser does get through, but that cannot run on a server.
  - APFIPP's calculator API covers 58 PPR funds across all 9 major managers
    and ~20 years, but returns only two aggregate numbers per query, not a
    time series -- it cannot populate a chart.
  - IMGA's chart API (apicharts.imga.pt) serves real daily series for 13 PPR
    funds, but its history is rebased to 10,000 and starts 2018-2021.
  - tools.morningstar.pt does not resolve.

APFIPP is still used as an independent cross-check of the returns implied by
this series (see scripts/verify_ppr_data.py).
"""
import datetime as dt
import json
import re
import time
from decimal import Decimal
from typing import Dict, List

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# The endpoint returns each fund's full available history and ignores dates
# earlier than its inception, so this is set well before any Portuguese PPR
# fund existed. Optimize's oldest series begins 2008-09-25.
HISTORY_START = "1990-01-01"

# Sanity bounds for a PPR unit value in EUR.
MIN_PLAUSIBLE_UP = Decimal("0.5")
MAX_PLAUSIBLE_UP = Decimal("1000")


class PPRDataError(RuntimeError):
    """Raised when real PPR data cannot be retrieved or fails validation."""


# The Optimize PPR range. ISINs are read back from each page and verified
# against these, so a silent product change breaks loudly instead of
# attaching the wrong history to a fund name.
OPTIMIZE_FUNDS = [
    {
        "slug": "ativo",
        "isin": "PTOPZAHM0003",
        "nome": "Optimize PPR Ativo",
        "gestor": "Optimize Investment Partners",
        "categoria": "PPR Ações",
    },
    {
        "slug": "equilibrado",
        "isin": "PTOPZBHM0002",
        "nome": "Optimize PPR Equilibrado",
        "gestor": "Optimize Investment Partners",
        "categoria": "PPR Misto",
    },
    {
        "slug": "moderado",
        "isin": "PTOPZDHM0000",
        "nome": "Optimize PPR Moderado",
        "gestor": "Optimize Investment Partners",
        "categoria": "PPR Moderado",
    },
    {
        "slug": "agressivo",
        "isin": "PTOPZEHM0017",
        "nome": "Optimize PPR Agressivo",
        "gestor": "Optimize Investment Partners",
        "categoria": "PPR Ações",
    },
]


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-PT,pt;q=0.9"},
        timeout=40,
        follow_redirects=True,
    )


def _get_ajax_config(client: httpx.Client, slug: str) -> tuple:
    """
    Read the per-page AJAX config (action + nonce) and the ISIN the page
    actually declares. The nonce is short-lived, so it must be scraped fresh
    rather than hardcoded.
    """
    url = f"https://optimize.pt/ppr/{slug}/"
    last_error = None
    for attempt in range(4):
        try:
            html = client.get(url).text
            break
        except Exception as exc:
            last_error = exc
            if attempt == 3:
                raise PPRDataError(f"Could not load {url}: {last_error}")
            time.sleep(2 * (attempt + 1))

    match = re.search(r'(\{"ajax".*?\}\})', html)
    if not match:
        raise PPRDataError(
            f"AJAX config not found on {url}. The site layout likely changed."
        )
    config = json.loads(match.group(1))["ajax"]

    page_isins = set(re.findall(r"data-symbol='([A-Z0-9]{12})'", html))
    return config, page_isins


def fetch_fund_nav(
    client: httpx.Client, fund: dict, start: str = HISTORY_START
) -> Dict[dt.date, Decimal]:
    """Fetch the real daily NAV series for one Optimize PPR fund."""
    config, page_isins = _get_ajax_config(client, fund["slug"])

    if page_isins and fund["isin"] not in page_isins:
        raise PPRDataError(
            f"{fund['nome']}: expected ISIN {fund['isin']} but page declares "
            f"{sorted(page_isins)}. Refusing to attach mismatched history."
        )

    last_error = None
    for attempt in range(4):
        try:
            response = client.post(
                config["url"],
                data={
                    "action": config["action"],
                    "nonce": config["nonce"],
                    "symbol": fund["isin"],
                    "type": "line",
                    "min_date": start,
                },
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt == 3:
                raise PPRDataError(f"{fund['nome']}: request failed: {last_error}")
            time.sleep(2 * (attempt + 1))

    if payload.get("status") != "OK":
        raise PPRDataError(f"{fund['nome']}: endpoint returned {payload.get('status')}")

    rows = payload.get("data") or []
    series: Dict[dt.date, Decimal] = {}
    for row in rows:
        # First row is the header pair ['Year', 'Valor da UP'].
        if not isinstance(row, list) or len(row) != 2:
            continue
        try:
            day = dt.date.fromisoformat(str(row[0]))
        except ValueError:
            continue
        value = Decimal(str(row[1]))
        if value > 0:
            series[day] = value

    validate_nav(fund["nome"], series)
    return series


def validate_nav(nome: str, series: Dict[dt.date, Decimal], min_days: int = 500) -> None:
    """
    Guard against seeding implausible or stale NAV data.

    Raises PPRDataError rather than letting bad data reach the database.
    """
    if len(series) < min_days:
        raise PPRDataError(
            f"{nome}: only {len(series)} NAV observations, expected >= {min_days}."
        )

    bad = [
        (day, value)
        for day, value in series.items()
        if not (MIN_PLAUSIBLE_UP <= value <= MAX_PLAUSIBLE_UP)
    ]
    if bad:
        raise PPRDataError(f"{nome}: implausible NAV values, e.g. {bad[:3]}")

    newest = max(series)
    staleness = (dt.date.today() - newest).days
    if staleness > 10:
        raise PPRDataError(
            f"{nome}: newest NAV is {newest} ({staleness} days old). Source is stale."
        )

    # A daily NAV series should not contain violent single-day jumps; those
    # indicate a unit split or a parsing error, not a real fund movement.
    days = sorted(series)
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days > 10:
            continue  # tolerate genuine reporting gaps
        change = abs(series[curr] / series[prev] - 1)
        if change > Decimal("0.35"):
            raise PPRDataError(
                f"{nome}: implausible {change:.0%} move {prev} -> {curr}. "
                f"Possible split or parse error."
            )


def fetch_all_funds(start: str = HISTORY_START) -> List[dict]:
    """
    Fetch every configured PPR fund with its real daily NAV series.

    Returns a list of fund dicts each carrying a `nav` mapping.
    """
    results = []
    with _client() as client:
        for fund in OPTIMIZE_FUNDS:
            nav = fetch_fund_nav(client, fund, start=start)
            results.append({**fund, "nav": nav})
            print(
                f"  [OK] {fund['nome']}: {len(nav)} daily NAV points "
                f"({min(nav)} -> {max(nav)})"
            )
    return results
