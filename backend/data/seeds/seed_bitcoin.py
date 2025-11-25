"""
Seed script to populate the database with Bitcoin historical data
Uses CoinGecko API to fetch real historical data
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal, engine, Base
from models.bitcoin import BitcoinHistoricalData
from datetime import datetime, timedelta
import requests
import time

def fetch_coingecko_data(days=1825):
    """
    Fetch Bitcoin historical data from CoinGecko API (free, no key needed)

    Args:
        days: Number of days of historical data (default: 1825 = ~5 years)
    """
    print(f"Fetching {days} days of Bitcoin data from CoinGecko...")

    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {
        "vs_currency": "eur",
        "days": days,
        "interval": "daily"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        prices = data.get("prices", [])
        print(f"  [OK] Fetched {len(prices)} price points")

        return prices
    except Exception as e:
        print(f"  [ERROR] Error fetching from CoinGecko: {e}")
        print("  [INFO] Using fallback sample data instead...")
        return None


def generate_sample_data():
    """
    Generate sample Bitcoin data if API fails
    This creates realistic-looking data for testing
    """
    print("Generating sample Bitcoin data...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=1825)  # 5 years

    data = []
    current_date = start_date
    base_price = 3000.0  # Starting price ~5 years ago
    current_price = base_price

    # Simulate Bitcoin's volatile growth
    while current_date <= end_date:
        # Bitcoin-like volatility
        import random
        daily_change = random.uniform(-0.08, 0.08)  # ±8% daily
        trend = 0.002  # Small upward trend

        current_price *= (1 + daily_change + trend)
        current_price = max(1000, current_price)  # Floor price

        timestamp = int(current_date.timestamp() * 1000)
        data.append([timestamp, current_price])

        current_date += timedelta(days=1)

    print(f"  [OK] Generated {len(data)} sample data points")
    return data


def seed_bitcoin():
    """Seed database with Bitcoin historical data"""

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Check if Bitcoin data already exists
    existing_count = db.query(BitcoinHistoricalData).count()
    if existing_count > 0:
        print(f"Database already has {existing_count} Bitcoin records. Skipping seed.")
        db.close()
        return

    print("Seeding Bitcoin historical data...")

    # Try to fetch real data from CoinGecko
    prices = fetch_coingecko_data(days=1825)

    # Fallback to sample data if API fails
    if not prices:
        prices = generate_sample_data()

    print(f"Processing {len(prices)} Bitcoin price records...")

    # Insert data in batches for better performance
    batch_size = 100
    records = []

    for i, (timestamp, price) in enumerate(prices):
        # Convert timestamp to date
        date = datetime.fromtimestamp(timestamp / 1000).date()

        # Use Portuguese column names: data, preco_eur, volume, market_cap
        record = BitcoinHistoricalData(
            data=date,
            preco_eur=round(price, 2),
            volume=0.0,  # CoinGecko free tier doesn't provide volume in history
            market_cap=0.0   # CoinGecko free tier doesn't provide market cap in history
        )
        records.append(record)

        # Insert in batches
        if len(records) >= batch_size:
            db.bulk_save_objects(records)
            db.commit()
            print(f"  Inserted {i + 1}/{len(prices)} records...", end="\r")
            records = []

    # Insert remaining records
    if records:
        db.bulk_save_objects(records)
        db.commit()

    print(f"\n[SUCCESS] Seeded {len(prices)} Bitcoin historical records!")
    db.close()


if __name__ == "__main__":
    seed_bitcoin()
