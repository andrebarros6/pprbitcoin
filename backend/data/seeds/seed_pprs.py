"""
Seed script to populate the database with real Portuguese PPR funds.

Source: Optimize Investment Partners' published daily NAV series
(see services/ppr_history.py).

There is deliberately NO synthetic fallback. An earlier version invented both
the fund list (plausible-looking names with fabricated ISINs) and their
performance (a random walk around a hardcoded average return). Publishing
invented performance against real, named, regulated funds is not acceptable,
so this script now seeds only funds whose real daily NAV it can actually
retrieve, and exits non-zero otherwise.

taxa_gestao is intentionally left NULL: the published NAV is already net of
management fees, and the fee is not machine-readable from the source. Storing
a guessed fee would misstate a real product's costs.
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal, engine, Base  # noqa: E402
from models.ppr import PPR, PPRHistoricalData  # noqa: E402
from services.ppr_history import fetch_all_funds, PPRDataError  # noqa: E402

BATCH_SIZE = 500


def seed_pprs(refresh: bool = False) -> int:
    """
    Seed PPR funds and their real daily NAV history.

    Args:
        refresh: If True, delete existing PPRs and re-seed. Required to
                 replace the synthetic funds seeded by the old version.

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

        # Fetch and validate everything BEFORE touching the database.
        print("Fetching real PPR daily NAV history...")
        funds = fetch_all_funds()

        if refresh and existing_count > 0:
            print(f"  Removing {existing_count} existing PPRs and their history...")
            db.query(PPRHistoricalData).delete()
            db.query(PPR).delete()
            db.commit()

        total_written = 0
        for fund in funds:
            ppr = PPR(
                nome=fund["nome"],
                gestor=fund["gestor"],
                isin=fund["isin"],
                categoria=fund["categoria"],
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
    args = parser.parse_args()

    try:
        seed_pprs(refresh=args.refresh)
    except PPRDataError as exc:
        print(f"\n[FAILED] Could not obtain real PPR data: {exc}", file=sys.stderr)
        print("Nothing was written to the database.", file=sys.stderr)
        sys.exit(1)
