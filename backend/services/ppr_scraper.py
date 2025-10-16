"""
PPR scraper service for collecting quota values from fund managers
"""
import asyncio
import aiohttp
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
import re

from models.ppr import PPR, PPRHistoricalData
from database import SessionLocal


class PPRScraper:
    """
    Base class for PPR scrapers
    """

    def __init__(self):
        self.session = None

    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    def clean_decimal(self, value: str) -> Optional[Decimal]:
        """
        Clean and convert string to Decimal

        Args:
            value: String value with currency format

        Returns:
            Decimal value or None
        """
        if not value:
            return None

        # Remove currency symbols, spaces, and replace comma with dot
        cleaned = re.sub(r'[€\s]', '', value)
        cleaned = cleaned.replace(',', '.')

        try:
            return Decimal(cleaned)
        except:
            return None

    async def scrape_ppr(self, ppr: PPR) -> Optional[Dict]:
        """
        Scrape quota value for a specific PPR
        Must be implemented by subclasses

        Args:
            ppr: PPR model instance

        Returns:
            Dict with quota data or None
        """
        raise NotImplementedError("Subclasses must implement scrape_ppr()")

    def save_historical_data(self, ppr_id, data: date, valor_quota: Decimal, db: Session) -> bool:
        """
        Save PPR historical data to database

        Args:
            ppr_id: PPR UUID
            data: Date of the quota
            valor_quota: Quota value
            db: Database session

        Returns:
            True if saved, False if already exists
        """
        # Check if already exists
        existing = db.query(PPRHistoricalData).filter(
            PPRHistoricalData.ppr_id == ppr_id,
            PPRHistoricalData.data == data
        ).first()

        if existing:
            # Update existing record
            existing.valor_quota = valor_quota
            return False
        else:
            # Insert new record
            new_record = PPRHistoricalData(
                ppr_id=ppr_id,
                data=data,
                valor_quota=valor_quota
            )
            db.add(new_record)
            return True


class ManualPPRDataProvider:
    """
    Manual data provider for PPRs when scraping is not available
    Allows manual input of quota values
    """

    def add_historical_data(self, ppr_id, records: List[Dict]):
        """
        Add multiple historical records for a PPR

        Args:
            ppr_id: PPR UUID
            records: List of dicts with 'data' and 'valor_quota'
        """
        db = SessionLocal()
        count = 0

        try:
            scraper = PPRScraper()

            for record in records:
                if scraper.save_historical_data(
                    ppr_id,
                    record['data'],
                    record['valor_quota'],
                    db
                ):
                    count += 1

            db.commit()
            print(f"✅ Added {count} new records")

        except Exception as e:
            db.rollback()
            print(f"❌ Error: {e}")
            raise
        finally:
            db.close()


class PPRScraperManager:
    """
    Manager to coordinate scraping of multiple PPRs
    """

    def __init__(self):
        self.scrapers = {}

    def register_scraper(self, gestor: str, scraper_class):
        """
        Register a scraper for a specific fund manager

        Args:
            gestor: Name of fund manager
            scraper_class: Scraper class to use
        """
        self.scrapers[gestor] = scraper_class

    async def scrape_all(self) -> Dict:
        """
        Scrape all PPRs in database

        Returns:
            Dict with results
        """
        db = SessionLocal()
        results = {
            "success": 0,
            "failed": 0,
            "errors": []
        }

        try:
            pprs = db.query(PPR).all()

            for ppr in pprs:
                try:
                    # Check if we have a scraper for this manager
                    if ppr.gestor in self.scrapers:
                        scraper_class = self.scrapers[ppr.gestor]
                        scraper = scraper_class()

                        # Scrape data
                        data = await scraper.scrape_ppr(ppr)

                        if data:
                            # Save to database
                            if scraper.save_historical_data(
                                ppr.id,
                                data['data'],
                                data['valor_quota'],
                                db
                            ):
                                results["success"] += 1
                                print(f"✓ {ppr.nome}: {data['valor_quota']} EUR")
                            else:
                                print(f"↻ {ppr.nome}: Already up to date")

                        await scraper.close()
                    else:
                        print(f"⚠️  {ppr.nome}: No scraper available for {ppr.gestor}")

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "ppr": ppr.nome,
                        "error": str(e)
                    })
                    print(f"✗ {ppr.nome}: {str(e)}")

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"❌ Fatal error: {e}")
            raise
        finally:
            db.close()

        return results


# Example scraper implementation (template)
class GNBPPRScraper(PPRScraper):
    """
    Scraper for GNB PPR funds
    Note: This is a template - actual implementation needs real URLs and selectors
    """

    async def scrape_ppr(self, ppr: PPR) -> Optional[Dict]:
        """
        Scrape GNB PPR quota value
        """
        # NOTE: This is a template - replace with actual GNB URL and logic
        url = "https://www.gnb.pt/fundos"  # Example URL

        session = await self.get_session()

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Example selector - needs to be adapted to real website
                    # quota_element = soup.select_one('.quota-value')
                    # if quota_element:
                    #     valor_quota = self.clean_decimal(quota_element.text)
                    #     return {
                    #         'data': datetime.now().date(),
                    #         'valor_quota': valor_quota
                    #     }

                    # Placeholder return
                    return None

        except Exception as e:
            print(f"Error scraping GNB: {e}")
            return None


if __name__ == "__main__":
    print("PPR Scraper Module")
    print("Use PPRScraperManager to coordinate scraping operations")