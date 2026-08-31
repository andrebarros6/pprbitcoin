"""
PPR daily NAV fetcher for funds whose manager publishes no accessible feed.

Source: Investing.com's historical-data API. This module exists for funds
that are otherwise unreachable -- Alves Ribeiro's manager (Invest Gestao de
Activos) has no resolvable website, and Banco Invest's fund API returns only
a current snapshot with no history.

IMPORTANT -- this fetcher cannot run headless or on a server.

Investing.com is behind Cloudflare, and three access routes were tried:

  - Plain server-side httpx: HTTP 403.
  - Headless Chrome: HTTP 403 (headless is detected).
  - A fetch() from inside the page: blocked by CORS.

What works is a *visible* Chrome window navigated directly to the API URL, so
the request is same-origin and carries the browser's real session. That means
this is a periodic manual refresh run on a workstation, not something the
scheduler can call. Seeded data from here is therefore a snapshot: re-run
this module by hand to update it.

Fund identity must never be taken from an Investing.com page title -- it
lists funds under outdated names (see DATA_SOURCES.md). Every fund below was
identified by matching its NAV-implied returns against the CMVM register.
"""
import datetime as dt
import json
from decimal import Decimal
from typing import Dict, List

API_TEMPLATE = (
    "https://api.investing.com/api/financialdata/{pair_id}"
    "/historical/chart/?period=MAX&interval=P1D&pointscount=160"
)

# Sanity bounds for a PPR unit value in EUR.
MIN_PLAUSIBLE_UP = Decimal("0.5")
MAX_PLAUSIBLE_UP = Decimal("1000")


class InvestingDataError(RuntimeError):
    """Raised when data cannot be retrieved or fails validation."""


# pair_id is Investing.com's internal identifier, read from the fund's
# historical-data page. `cmvm_name` records the identity confirmed by return
# matching, so the fund can be re-verified without repeating the search.
INVESTING_FUNDS = [
    {
        "pair_id": "1011177",
        "slug": "alves-ribeiro-ppr-fundo-de-invest",
        "isin": "PTARMCLM0004",
        "nome": "Alves Ribeiro PPR",
        "gestor": "Invest Gestão de Activos",
        "categoria": "PPR Misto",
        # Confirmed against CMVM at 2025-12-31: 1y 4.77 vs 4.77,
        # 10y 4.74 vs 4.67, mean deviation 0.06pp across five horizons.
        "cmvm_name": "ALVES RIBEIRO PPR / OICVM",
    },
]


def _new_driver():
    """A visible (non-headless) Chrome. See the module docstring."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise InvestingDataError(
            "selenium is required for this fetcher; it cannot use httpx."
        ) from exc

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1400,1000")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator,"webdriver",{get:()=>undefined})'},
    )
    driver.set_page_load_timeout(120)
    return driver


def fetch_fund_nav(
    driver, fund: dict, settle: int = 12, attempts: int = 3
) -> Dict[dt.date, Decimal]:
    """
    Fetch one fund's full daily NAV series.

    Cloudflare rate-limits rapid successive requests, so each attempt
    re-warms on the fund page and waits longer than the last before asking
    for the API URL.
    """
    import time

    body = ""
    for attempt in range(attempts):
        pause = settle * (attempt + 1)

        # Load the fund page first so the API request carries a warmed session.
        driver.get(f"https://www.investing.com/funds/{fund['slug']}-historical-data")
        time.sleep(pause)

        driver.get(API_TEMPLATE.format(pair_id=fund["pair_id"]))
        time.sleep(pause)
        body = driver.find_element("tag name", "body").text

        if body.startswith("{"):
            break
        if attempt < attempts - 1:
            time.sleep(pause * 2)

    if not body.startswith("{"):
        raise InvestingDataError(
            f"{fund['nome']}: request blocked (Cloudflare) after {attempts} "
            f"attempts. Retry more slowly, and confirm the browser is not "
            f"headless."
        )

    try:
        rows = json.loads(body)["data"]
    except (ValueError, KeyError) as exc:
        raise InvestingDataError(f"{fund['nome']}: unexpected payload: {exc}") from exc

    series: Dict[dt.date, Decimal] = {}
    for row in rows:
        day = dt.datetime.fromtimestamp(row[0] / 1000, dt.timezone.utc).date()
        close = Decimal(str(row[4]))  # [timestamp, open, high, low, close, ...]
        if close > 0:
            series[day] = close

    validate_nav(fund["nome"], series)
    return series


def validate_nav(nome: str, series: Dict[dt.date, Decimal], min_days: int = 500) -> None:
    """
    Guard against seeding implausible data.

    Staleness is deliberately NOT checked here. This source is refreshed by
    hand, so a series being weeks old is expected rather than a fault; the
    seed records the last observation date instead.
    """
    if len(series) < min_days:
        raise InvestingDataError(
            f"{nome}: only {len(series)} observations, expected >= {min_days}."
        )

    bad = [
        (day, value)
        for day, value in series.items()
        if not (MIN_PLAUSIBLE_UP <= value <= MAX_PLAUSIBLE_UP)
    ]
    if bad:
        raise InvestingDataError(f"{nome}: implausible NAV values, e.g. {bad[:3]}")

    days = sorted(series)
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days > 10:
            continue  # tolerate genuine reporting gaps
        change = abs(series[curr] / series[prev] - 1)
        if change > Decimal("0.35"):
            raise InvestingDataError(
                f"{nome}: implausible {change:.0%} move {prev} -> {curr}. "
                f"Possible split or parse error."
            )


def fetch_all_funds() -> List[dict]:
    """Fetch every configured fund. Opens one visible browser for all of them."""
    driver = _new_driver()
    try:
        results = []
        for fund in INVESTING_FUNDS:
            nav = fetch_fund_nav(driver, fund)
            results.append({**fund, "nav": nav})
            print(
                f"  [OK] {fund['nome']}: {len(nav)} daily NAV points "
                f"({min(nav)} -> {max(nav)})"
            )
        return results
    finally:
        driver.quit()
