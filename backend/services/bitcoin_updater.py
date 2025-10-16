"""
Bitcoin data updater service using CoinGecko API
"""
import aiohttp
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from models.bitcoin import BitcoinHistoricalData
from database import SessionLocal


class BitcoinUpdater:
    """
    Service to fetch and update Bitcoin price data from CoinGecko API
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Bitcoin updater

        Args:
            api_key: Optional CoinGecko API key for higher rate limits
        """
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["x-cg-pro-api-key"] = api_key

    async def get_current_price(self) -> Dict:
        """
        Get current Bitcoin price in EUR

        Returns:
            Dict with current price data
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "eur",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }

            async with session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "preco_eur": Decimal(str(data['bitcoin']['eur'])),
                        "volume": Decimal(str(data['bitcoin'].get('eur_24h_vol', 0))),
                        "market_cap": Decimal(str(data['bitcoin'].get('eur_market_cap', 0)))
                    }
                else:
                    raise Exception(f"CoinGecko API error: {response.status}")

    async def get_historical_data(self, days: int = 365) -> List[Dict]:
        """
        Get historical Bitcoin price data

        Args:
            days: Number of days of historical data (max: 'max' for all data)

        Returns:
            List of daily price data
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/coins/bitcoin/market_chart"
            params = {
                "vs_currency": "eur",
                "days": days,
                "interval": "daily"
            }

            async with session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Process data
                    historical_data = []
                    for i, price_point in enumerate(data['prices']):
                        timestamp_ms = price_point[0]
                        price = Decimal(str(price_point[1]))

                        # Get volume if available
                        volume = Decimal(str(data['total_volumes'][i][1])) if i < len(data['total_volumes']) else None

                        historical_data.append({
                            "data": datetime.fromtimestamp(timestamp_ms / 1000).date(),
                            "preco_eur": price,
                            "volume": volume,
                            "market_cap": None  # Not available in this endpoint
                        })

                    return historical_data
                else:
                    raise Exception(f"CoinGecko API error: {response.status}")

    async def get_historical_range(self, from_date: datetime, to_date: datetime) -> List[Dict]:
        """
        Get historical data for a specific date range

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of daily price data
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/coins/bitcoin/market_chart/range"
            params = {
                "vs_currency": "eur",
                "from": int(from_date.timestamp()),
                "to": int(to_date.timestamp())
            }

            async with session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()

                    historical_data = []
                    for i, price_point in enumerate(data['prices']):
                        timestamp_ms = price_point[0]
                        price = Decimal(str(price_point[1]))

                        volume = Decimal(str(data['total_volumes'][i][1])) if i < len(data['total_volumes']) else None

                        historical_data.append({
                            "data": datetime.fromtimestamp(timestamp_ms / 1000).date(),
                            "preco_eur": price,
                            "volume": volume,
                            "market_cap": None
                        })

                    return historical_data
                else:
                    raise Exception(f"CoinGecko API error: {response.status}")

    def save_to_database(self, data: List[Dict], db: Session) -> int:
        """
        Save Bitcoin data to database

        Args:
            data: List of price data dictionaries
            db: Database session

        Returns:
            Number of records inserted/updated
        """
        count = 0

        for record in data:
            # Check if record already exists
            existing = db.query(BitcoinHistoricalData).filter(
                BitcoinHistoricalData.data == record['data']
            ).first()

            if existing:
                # Update existing record
                existing.preco_eur = record['preco_eur']
                existing.volume = record.get('volume')
                existing.market_cap = record.get('market_cap')
            else:
                # Insert new record
                new_record = BitcoinHistoricalData(**record)
                db.add(new_record)

            count += 1

        db.commit()
        return count

    async def update_latest(self) -> Dict:
        """
        Update database with latest Bitcoin price

        Returns:
            Dict with update info
        """
        db = SessionLocal()
        try:
            current_data = await self.get_current_price()

            # Add today's date
            today = datetime.now().date()
            current_data['data'] = today

            # Save to database
            count = self.save_to_database([current_data], db)

            return {
                "success": True,
                "records_updated": count,
                "date": today,
                "price": float(current_data['preco_eur'])
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()

    async def populate_historical(self, days: int = 365) -> Dict:
        """
        Populate database with historical Bitcoin data

        Args:
            days: Number of days to fetch (use 'max' for all available data)

        Returns:
            Dict with operation info
        """
        db = SessionLocal()
        try:
            print(f"Fetching {days} days of Bitcoin historical data from CoinGecko...")

            historical_data = await self.get_historical_data(days)

            print(f"Saving {len(historical_data)} records to database...")
            count = self.save_to_database(historical_data, db)

            return {
                "success": True,
                "records_processed": count,
                "date_range": {
                    "from": historical_data[0]['data'].isoformat() if historical_data else None,
                    "to": historical_data[-1]['data'].isoformat() if historical_data else None
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()


# CLI usage
if __name__ == "__main__":
    import sys

    updater = BitcoinUpdater()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "update":
            # Update with latest price
            result = asyncio.run(updater.update_latest())
            print(f"✅ Updated: {result}")

        elif command == "populate":
            # Populate with historical data
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 1825  # 5 years default
            result = asyncio.run(updater.populate_historical(days))
            print(f"✅ Populated: {result}")

        else:
            print("Usage:")
            print("  python bitcoin_updater.py update          # Update latest price")
            print("  python bitcoin_updater.py populate [days] # Populate historical data")
    else:
        print("Usage:")
        print("  python bitcoin_updater.py update          # Update latest price")
        print("  python bitcoin_updater.py populate [days] # Populate historical data")