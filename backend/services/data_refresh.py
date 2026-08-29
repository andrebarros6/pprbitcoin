"""
Scheduled refresh of Bitcoin and PPR data from the verified sources.

Uses the same fetchers as the seed scripts (services/bitcoin_history.py and
services/ppr_history.py) so the daily updates cannot drift onto a different --
or synthetic -- source than the one the database was seeded from.

Both routines upsert by date and never write partial or unvalidated data: a
failed fetch is reported and leaves the existing rows untouched.
"""
import datetime as dt
import logging
from typing import Dict

from database import SessionLocal
from models.bitcoin import BitcoinHistoricalData
from models.ppr import PPR, PPRHistoricalData
from services.bitcoin_history import fetch_btc_eur_daily, BitcoinDataError
from services.ppr_history import fetch_all_funds, PPRDataError
from services.imga_history import (
    fetch_all_funds as fetch_imga_funds,
    IMGADataError,
)

logger = logging.getLogger(__name__)

# How far back a scheduled run re-checks. Short window keeps the job cheap
# while still backfilling late-published values and correcting restatements.
REFRESH_LOOKBACK_DAYS = 30


def refresh_bitcoin() -> Dict:
    """Fetch recent BTC/EUR closes and upsert them."""
    start = dt.date.today() - dt.timedelta(days=REFRESH_LOOKBACK_DAYS)
    db = SessionLocal()
    try:
        # fetch_btc_eur_daily validates before returning; a bad response
        # raises rather than handing back junk.
        prices = fetch_btc_eur_daily()
        recent = {day: price for day, price in prices.items() if day >= start}

        inserted = updated = 0
        for day, price in sorted(recent.items()):
            row = (
                db.query(BitcoinHistoricalData)
                .filter(BitcoinHistoricalData.data == day)
                .first()
            )
            if row is None:
                db.add(BitcoinHistoricalData(
                    data=day, preco_eur=price, volume=0.0, market_cap=0.0,
                ))
                inserted += 1
            elif row.preco_eur != price:
                row.preco_eur = price
                updated += 1

        db.commit()
        logger.info("Bitcoin refresh: %d inserted, %d updated", inserted, updated)
        return {"success": True, "inserted": inserted, "updated": updated}

    except BitcoinDataError as exc:
        db.rollback()
        logger.error("Bitcoin refresh failed, existing data untouched: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


def refresh_pprs() -> Dict:
    """Fetch recent PPR NAV values for every seeded fund and upsert them."""
    start = dt.date.today() - dt.timedelta(days=REFRESH_LOOKBACK_DAYS)
    db = SessionLocal()
    try:
        funds = fetch_all_funds() + fetch_imga_funds()

        inserted = updated = 0
        for fund in funds:
            # Optimize funds are identified by ISIN. The IMGA/EuroBic series
            # have no ISIN in the source, so those match on name instead.
            isin = fund.get("isin")
            if isin:
                ppr = db.query(PPR).filter(PPR.isin == isin).first()
            else:
                ppr = db.query(PPR).filter(PPR.nome == fund["nome"]).first()

            if ppr is None:
                logger.warning(
                    "PPR %s (%s) not in database; run the seed script first.",
                    fund["nome"], isin or "no ISIN",
                )
                continue

            recent = {d: v for d, v in fund["nav"].items() if d >= start}
            for day, value in sorted(recent.items()):
                row = (
                    db.query(PPRHistoricalData)
                    .filter(
                        PPRHistoricalData.ppr_id == ppr.id,
                        PPRHistoricalData.data == day,
                    )
                    .first()
                )
                if row is None:
                    db.add(PPRHistoricalData(
                        ppr_id=ppr.id, data=day, valor_quota=value,
                    ))
                    inserted += 1
                elif row.valor_quota != value:
                    row.valor_quota = value
                    updated += 1

        db.commit()
        logger.info("PPR refresh: %d inserted, %d updated", inserted, updated)
        return {"success": True, "inserted": inserted, "updated": updated}

    except (PPRDataError, IMGADataError) as exc:
        db.rollback()
        logger.error("PPR refresh failed, existing data untouched: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        db.close()
