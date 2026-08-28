"""
Copy the verified local dataset into the production (Postgres) database.

The local SQLite database holds the PPR NAV and Bitcoin price history that
scripts/verify_ppr_data.py has already cross-checked against APFIPP. Copying
it gives production a known-good baseline immediately, without depending on
the upstream sources being reachable at deploy time. The scheduler then keeps
it current from those same sources.

Usage:
    # Target database is read from TARGET_DATABASE_URL, falling back to
    # DATABASE_URL. Source defaults to the local SQLite file.
    TARGET_DATABASE_URL=postgresql://... python scripts/migrate_to_postgres.py

    # Preview without writing:
    ... python scripts/migrate_to_postgres.py --dry-run
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from config import settings  # noqa: E402
from database import Base  # noqa: E402
from models.bitcoin import BitcoinHistoricalData  # noqa: E402
from models.ppr import PPR, PPRHistoricalData  # noqa: E402

DEFAULT_SOURCE = "sqlite:///./pprbitcoin.db"
BATCH_SIZE = 1000


def normalise(url: str) -> str:
    """Apply the same postgres:// rewrite the app uses."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def engine_for(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def migrate(source_url: str, target_url: str, dry_run: bool = False) -> None:
    source_engine = engine_for(source_url)
    target_engine = engine_for(target_url)

    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    src = SourceSession()
    dst = TargetSession()

    try:
        pprs = src.query(PPR).all()
        nav_count = src.query(PPRHistoricalData).count()
        btc_count = src.query(BitcoinHistoricalData).count()

        print(f"Source: {len(pprs)} PPRs, {nav_count} NAV rows, {btc_count} BTC rows")

        if dry_run:
            print("[DRY RUN] Nothing written.")
            return

        Base.metadata.create_all(bind=target_engine)

        existing_pprs = dst.query(PPR).count()
        existing_btc = dst.query(BitcoinHistoricalData).count()
        if existing_pprs or existing_btc:
            print(
                f"Target already has {existing_pprs} PPRs and {existing_btc} BTC "
                f"rows. Clearing them so this migration is repeatable."
            )
            dst.query(PPRHistoricalData).delete()
            dst.query(PPR).delete()
            dst.query(BitcoinHistoricalData).delete()
            dst.commit()

        # --- PPRs and their history ---------------------------------
        # IDs are preserved so the NAV foreign keys stay valid.
        for ppr in pprs:
            dst.add(PPR(
                id=ppr.id,
                nome=ppr.nome,
                gestor=ppr.gestor,
                isin=ppr.isin,
                categoria=ppr.categoria,
                taxa_gestao=ppr.taxa_gestao,
            ))
        dst.commit()
        print(f"  Copied {len(pprs)} PPR funds")

        written = 0
        batch = []
        for row in src.query(PPRHistoricalData).yield_per(BATCH_SIZE):
            batch.append(PPRHistoricalData(
                id=row.id,
                ppr_id=row.ppr_id,
                data=row.data,
                valor_quota=row.valor_quota,
                rentabilidade_acumulada=row.rentabilidade_acumulada,
            ))
            if len(batch) >= BATCH_SIZE:
                dst.bulk_save_objects(batch)
                dst.commit()
                written += len(batch)
                batch = []
                print(f"  NAV rows: {written}/{nav_count}", end="\r")
        if batch:
            dst.bulk_save_objects(batch)
            dst.commit()
            written += len(batch)
        print(f"  Copied {written} NAV rows          ")

        # --- Bitcoin -------------------------------------------------
        written = 0
        batch = []
        for row in src.query(BitcoinHistoricalData).yield_per(BATCH_SIZE):
            batch.append(BitcoinHistoricalData(
                id=row.id,
                data=row.data,
                preco_eur=row.preco_eur,
                volume=row.volume,
                market_cap=row.market_cap,
            ))
            if len(batch) >= BATCH_SIZE:
                dst.bulk_save_objects(batch)
                dst.commit()
                written += len(batch)
                batch = []
                print(f"  BTC rows: {written}/{btc_count}", end="\r")
        if batch:
            dst.bulk_save_objects(batch)
            dst.commit()
            written += len(batch)
        print(f"  Copied {written} BTC rows          ")

        # --- Verify --------------------------------------------------
        final_pprs = dst.query(PPR).count()
        final_nav = dst.query(PPRHistoricalData).count()
        final_btc = dst.query(BitcoinHistoricalData).count()

        ok = (
            final_pprs == len(pprs)
            and final_nav == nav_count
            and final_btc == btc_count
        )
        print(
            f"\nTarget now has {final_pprs} PPRs, {final_nav} NAV rows, "
            f"{final_btc} BTC rows"
        )
        if not ok:
            raise RuntimeError("Row counts do not match source. Migration failed.")
        print("[SUCCESS] Migration complete and row counts match.")

    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local data to Postgres")
    parser.add_argument("--source", default=os.getenv("SOURCE_DATABASE_URL", DEFAULT_SOURCE))
    parser.add_argument(
        "--target",
        default=os.getenv("TARGET_DATABASE_URL") or settings.DATABASE_URL,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = normalise(args.target)
    if target.startswith("sqlite"):
        print(
            "Refusing to run: target is SQLite. Set TARGET_DATABASE_URL to the "
            "Postgres connection string (Railway: Variables -> DATABASE_URL).",
            file=sys.stderr,
        )
        sys.exit(1)

    migrate(normalise(args.source), target, dry_run=args.dry_run)
