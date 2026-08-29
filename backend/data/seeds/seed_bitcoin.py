"""
Seed script to populate the database with real Bitcoin historical data.

Source: Bitstamp public OHLC (see services/bitcoin_history.py).

There is deliberately NO synthetic fallback. An earlier version fell back to a
random walk when the API call failed, which silently filled the database with
prices that were never real. If the fetch or validation fails, this script
exits non-zero and writes nothing.
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal, engine, Base  # noqa: E402
from models.bitcoin import BitcoinHistoricalData  # noqa: E402
from services.bitcoin_history import fetch_btc_eur_daily, BitcoinDataError  # noqa: E402

BATCH_SIZE = 500


def seed_bitcoin(refresh: bool = False) -> int:
    """
    Seed Bitcoin historical data.

    Args:
        refresh: If True, delete existing rows and re-seed. Required to
                 replace data seeded by the old synthetic fallback.

    Returns:
        Number of records written.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing_count = db.query(BitcoinHistoricalData).count()
        if existing_count > 0 and not refresh:
            print(
                f"Database already has {existing_count} Bitcoin records. "
                f"Skipping seed. Use --refresh to replace them."
            )
            return 0

        # Fetch and validate BEFORE touching the database, so a failed fetch
        # never leaves the table empty or half-written.
        print("Fetching real BTC/EUR daily history from Bitstamp...")
        prices = fetch_btc_eur_daily()
        print(f"  [OK] {len(prices)} validated daily prices "
              f"({min(prices)} -> {max(prices)})")

        if refresh and existing_count > 0:
            print(f"  Removing {existing_count} existing records (--refresh)...")
            db.query(BitcoinHistoricalData).delete()
            db.commit()

        records = []
        written = 0
        for day in sorted(prices):
            records.append(
                BitcoinHistoricalData(
                    data=day,
                    preco_eur=prices[day],
                    # Bitstamp's daily OHLC volume is in BTC, not EUR, and the
                    # portfolio engine does not use it. Left at 0 rather than
                    # storing a figure in ambiguous units.
                    volume=0.0,
                    market_cap=0.0,
                )
            )
            if len(records) >= BATCH_SIZE:
                db.bulk_save_objects(records)
                db.commit()
                written += len(records)
                records = []
                print(f"  Inserted {written}/{len(prices)} records...", end="\r")

        if records:
            db.bulk_save_objects(records)
            db.commit()
            written += len(records)

        print(f"\n[SUCCESS] Seeded {written} real Bitcoin historical records!")
        return written

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed real Bitcoin price history")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Delete existing Bitcoin rows and re-seed from source",
    )
    args = parser.parse_args()

    try:
        seed_bitcoin(refresh=args.refresh)
    except BitcoinDataError as exc:
        print(f"\n[FAILED] Could not obtain real Bitcoin data: {exc}", file=sys.stderr)
        print("Nothing was written to the database.", file=sys.stderr)
        sys.exit(1)
