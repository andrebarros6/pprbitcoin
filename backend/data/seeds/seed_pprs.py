"""
Seed script to populate the database with real Portuguese PPR funds.

Sources:
  - Optimize Investment Partners' published daily NAV series
    (services/ppr_history.py), in EUR per unit.
  - IMGA's chart API for IMGA and EuroBic funds (services/imga_history.py),
    as a performance index rebased to 10,000 rather than a unit value.
  - Casa de Investimentos' chart API (services/casa_history.py), as a
    performance index rebased to 100.
  - Investing.com for funds with no reachable manager feed
    (services/investing_history.py), in EUR per unit. Opt-in via
    --with-investing because it needs a visible browser and so cannot run
    unattended; see that module's docstring.

All are real observed daily series. The index-based funds are marked in
`categoria` so the UI never presents an index as a unit price; returns and
risk metrics are unaffected because they depend only on ratios between
points.

There is deliberately NO synthetic fallback. An earlier version invented both
the fund list (plausible-looking names with fabricated ISINs) and their
performance (a random walk around a hardcoded average return). Publishing
invented performance against real, named, regulated funds is not acceptable,
so this script now seeds only funds whose real daily NAV it can actually
retrieve, and exits non-zero otherwise.

taxa_gestao is left NULL here and populated separately by
scripts/update_fees.py from the CMVM register, which publishes the Taxa de
Encargos Correntes. It is never guessed: the NAV is already net of fees, so a
made-up figure would misstate a real product's costs.
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal, engine, Base  # noqa: E402
from models.ppr import PPR, PPRHistoricalData  # noqa: E402
from services.ppr_history import fetch_all_funds, PPRDataError  # noqa: E402
from services.imga_history import (  # noqa: E402
    fetch_all_funds as fetch_imga_funds,
    IMGADataError,
)
from services.casa_history import (  # noqa: E402
    fetch_all_funds as fetch_casa_funds,
    CasaDataError,
)
from services.investing_history import (  # noqa: E402
    fetch_all_funds as fetch_investing_funds,
    InvestingDataError,
)

BATCH_SIZE = 500


def seed_pprs(refresh: bool = False, with_investing: bool = False) -> int:
    """
    Seed PPR funds and their real daily NAV history.

    Args:
        refresh: If True, delete existing PPRs and re-seed. Required to
                 replace the synthetic funds seeded by the old version.
        with_investing: Also seed funds sourced from Investing.com. Off by
                 default because that fetcher opens a visible browser window.

    Returns:
        Number of NAV records written.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing_count = db.query(PPR).count()
        if existing_count > 0 and not refresh:
            print(
                f"Database already has {existing_count} PPRs. Skipping seed. "
                f"Use --refresh to replace them."
            )
            return 0

        # Fetch and validate everything BEFORE touching the database, so a
        # failed fetch cannot leave a half-populated catalogue.
        print("Fetching real PPR daily NAV history (Optimize)...")
        funds = fetch_all_funds()

        print("Fetching real PPR daily series (IMGA / EuroBic)...")
        funds = funds + fetch_imga_funds()

        print("Fetching real PPR daily series (Casa de Investimentos)...")
        funds = funds + fetch_casa_funds()

        if with_investing:
            print("Fetching real PPR daily NAV (Investing.com, opens a browser)...")
            funds = funds + fetch_investing_funds()

        if refresh and existing_count > 0:
            print(f"  Removing {existing_count} existing PPRs and their history...")
            db.query(PPRHistoricalData).delete()
            db.query(PPR).delete()
            db.commit()

        total_written = 0
        for fund in funds:
            # Some sources publish a rebased performance index rather than a
            # unit value in EUR -- IMGA/EuroBic to 10,000, Casa to 100. Those
            # funds carry no ISIN here, so that is the marker. Tagging the
            # category keeps the distinction visible downstream.
            categoria = fund["categoria"]
            if "isin" not in fund:
                categoria = f"{categoria} (índice)"

            ppr = PPR(
                nome=fund["nome"],
                gestor=fund["gestor"],
                isin=fund.get("isin"),
                categoria=categoria,
                taxa_gestao=None,  # see module docstring
            )
            db.add(ppr)
            db.commit()
            db.refresh(ppr)

            nav = fund["nav"]
            days = sorted(nav)
            baseline = nav[days[0]]

            records = []
            for day in days:
                value = nav[day]
                records.append(
                    PPRHistoricalData(
                        ppr_id=ppr.id,
                        data=day,
                        valor_quota=value,
                        # Cumulative return since the first observation, in %.
                        rentabilidade_acumulada=(value / baseline - 1) * 100,
                    )
                )
                if len(records) >= BATCH_SIZE:
                    db.bulk_save_objects(records)
                    db.commit()
                    total_written += len(records)
                    records = []

            if records:
                db.bulk_save_objects(records)
                db.commit()
                total_written += len(records)

            print(f"  Seeded {fund['nome']} ({len(days)} NAV points)")

        print(
            f"\n[SUCCESS] Seeded {len(funds)} real PPR funds "
            f"with {total_written} NAV records!"
        )
        return total_written

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed real PPR funds and NAV history")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Delete existing PPRs and re-seed from source",
    )
    parser.add_argument(
        "--with-investing",
        action="store_true",
        help=(
            "Also seed funds sourced from Investing.com. Opens a visible "
            "browser window, so it cannot run unattended or on a server."
        ),
    )
    args = parser.parse_args()

    try:
        seed_pprs(refresh=args.refresh, with_investing=args.with_investing)
    except (PPRDataError, IMGADataError, CasaDataError, InvestingDataError) as exc:
        print(f"\n[FAILED] Could not obtain real PPR data: {exc}", file=sys.stderr)
        print("Nothing was written to the database.", file=sys.stderr)
        sys.exit(1)
