"""
Independent verification that the seeded data is real.

Cross-checks the annualised returns implied by the seeded PPR NAV series
against the figures APFIPP publishes for the same funds, and sanity-checks
Bitcoin prices against known historical values.

APFIPP is an independent source from the fund manager, so agreement between
the two is strong evidence the stored series is genuine. Run this after any
re-seed.
"""
import datetime as dt
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx  # noqa: E402
import pandas as pd  # noqa: E402

from database import SessionLocal  # noqa: E402
from models.bitcoin import BitcoinHistoricalData  # noqa: E402
from models.ppr import PPR, PPRHistoricalData  # noqa: E402

APFIPP_URL = "https://www.apfipp.pt/pt/estatisticas/rendibilidades/oic-mobiliario/"
# APFIPP's table is published with an as-of date in its first column header.
# Returns must be compared on that same date -- comparing a NAV-implied
# return measured today against a figure published weeks ago produces large
# spurious differences on the short horizons.
APFIPP_ASOF_RE = re.compile(r"(\d{2})/(\w+)\.?/(\d{4})")
PT_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Known real BTC/EUR closes, used as an independent spot-check.
BTC_REFERENCE = {
    dt.date(2021, 11, 10): 56000,   # all-time-high period
    dt.date(2022, 11, 21): 15500,   # post-FTX trough
}
BTC_TOLERANCE = 0.05  # 5%

# How far the NAV-implied return may differ from APFIPP's figure, in
# percentage points. The two are measured on different as-of dates, so exact
# agreement is not expected.
RETURN_TOLERANCE_PP = 0.75


def parse_apfipp_asof(raw_header: str) -> dt.date:
    """Read the as-of date out of the APFIPP table header, e.g. '07/ago./2026'."""
    match = APFIPP_ASOF_RE.search(raw_header)
    if not match:
        raise RuntimeError(f"Could not parse APFIPP as-of date from {raw_header!r}")
    day, month_name, year = match.groups()
    month = PT_MONTHS.get(month_name[:3].lower())
    if not month:
        raise RuntimeError(f"Unknown Portuguese month {month_name!r}")
    return dt.date(int(year), month, int(day))


def load_apfipp() -> tuple:
    response = httpx.get(
        APFIPP_URL, timeout=40, follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    response.encoding = "utf-8"
    table = pd.read_html(io.StringIO(response.text), decimal=",", thousands=".")[22]
    asof = parse_apfipp_asof(str(table.columns[0][0]))
    table.columns = [
        "nome", "moeda", "e1", "e2", "r3m", "r6m", "ytd",
        "r1a", "r2a", "r3a", "r5a",
        "k1", "k2", "k3", "k4", "k5", "k6", "k7", "up",
    ]
    return table, asof


def _apfipp_match_tokens(nome: str) -> tuple:
    """
    Map a stored fund name to (manager token, distinguishing token) as APFIPP
    spells them.

    APFIPP lists EuroBic's lifecycle funds under ABANCA, which acquired
    EuroBic, so the manager token cannot simply be taken from our own name.
    """
    if nome.startswith("EuroBic"):
        # "EuroBic PPR Ciclo de Vida 35-44" -> ABANCA + "35-44"
        return "ABANCA", nome.split()[-1]
    if nome.startswith("IMGA"):
        # "IMGA Investimento PPR Ações" -> IMGA + "Investimento"
        return "IMGA", nome.split()[1]
    # "Optimize PPR Ativo" -> Optimize + "Ativo"
    return nome.split()[0], nome.split()[-1]


def annualised(series: dict, years: int, asof: dt.date) -> float:
    """Annualised return over `years`, measured as of `asof`."""
    days = sorted(d for d in series if d <= asof)
    if not days:
        return float("nan")
    last = days[-1]
    target = last - dt.timedelta(days=365 * years)
    start = min(days, key=lambda d: abs(d - target))
    if start == last:
        return float("nan")
    return ((series[last] / series[start]) ** (1 / years) - 1) * 100


def main() -> int:
    db = SessionLocal()
    failures = []

    try:
        # --- Bitcoin -------------------------------------------------
        print("Bitcoin:")
        btc_count = db.query(BitcoinHistoricalData).count()
        print(f"  {btc_count} rows")
        if btc_count < 1000:
            failures.append(f"Bitcoin has only {btc_count} rows")

        for day, expected in BTC_REFERENCE.items():
            row = (
                db.query(BitcoinHistoricalData)
                .filter(BitcoinHistoricalData.data == day)
                .first()
            )
            if row is None:
                failures.append(f"Bitcoin missing reference date {day}")
                continue
            actual = float(row.preco_eur)
            drift = abs(actual - expected) / expected
            status = "OK" if drift <= BTC_TOLERANCE else "FAIL"
            print(f"  [{status}] {day}: EUR {actual:,.0f} (expected ~{expected:,})")
            if drift > BTC_TOLERANCE:
                failures.append(f"Bitcoin {day} = {actual}, expected ~{expected}")

        # --- PPRs ----------------------------------------------------
        print("\nPPR funds (NAV-implied vs APFIPP published):")
        apfipp, asof = load_apfipp()
        print(f"  (APFIPP figures as of {asof})")

        for ppr in db.query(PPR).all():
            rows = (
                db.query(PPRHistoricalData)
                .filter(PPRHistoricalData.ppr_id == ppr.id)
                .all()
            )
            series = {r.data: float(r.valor_quota) for r in rows}
            if not series:
                failures.append(f"{ppr.nome}: no NAV rows")
                continue

            # Match APFIPP's row on the manager plus the fund's distinguishing
            # words. APFIPP names EuroBic's lifecycle funds under ABANCA, which
            # acquired EuroBic, so the manager token differs from ours.
            family, key = _apfipp_match_tokens(ppr.nome)
            match = apfipp[
                apfipp["nome"].str.contains(family, na=False, case=False)
                & apfipp["nome"].str.contains(key, na=False, regex=False)
            ]

            print(f"\n  {ppr.nome} ({ppr.isin or 'index'}) - {len(series)} points")
            if match.empty:
                print("    (not listed by APFIPP - no cross-check available)")
                continue

            for years, column in [(1, "r1a"), (3, "r3a"), (5, "r5a")]:
                published = match.iloc[0][column]
                if pd.isna(published):
                    continue
                implied = annualised(series, years, asof)
                delta = abs(implied - float(published))
                status = "OK" if delta <= RETURN_TOLERANCE_PP else "FAIL"
                print(
                    f"    [{status}] {years}y: NAV-implied {implied:5.2f}% vs "
                    f"APFIPP {float(published):5.2f}%  (delta {delta:.2f}pp)"
                )
                if delta > RETURN_TOLERANCE_PP:
                    failures.append(
                        f"{ppr.nome} {years}y: {implied:.2f} vs {published:.2f}"
                    )

        print("\n" + "=" * 60)
        if failures:
            print(f"[FAILED] {len(failures)} check(s) did not pass:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print("[PASSED] All data verified against independent sources.")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
