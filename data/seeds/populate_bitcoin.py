"""
Script to populate Bitcoin historical data from CSV and CoinGecko API
"""
import sys
import os
import pandas as pd
import asyncio
from datetime import datetime
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from database import SessionLocal
from models.bitcoin import BitcoinHistoricalData
from services.bitcoin_updater import BitcoinUpdater


def load_csv_data(csv_path: str):
    """
    Load Bitcoin data from existing CSV file

    Args:
        csv_path: Path to CSV file
    """
    print(f"📂 Loading data from {csv_path}...")

    # Read CSV
    df = pd.read_csv(csv_path)

    # Convert date column
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')

    # Clean price column (remove commas and convert to float)
    df['Price'] = df['Price'].str.replace(',', '').astype(float)

    print(f"✅ Loaded {len(df)} records from CSV")

    # Save to database
    db = SessionLocal()
    count = 0

    try:
        for _, row in df.iterrows():
            # Check if already exists
            existing = db.query(BitcoinHistoricalData).filter(
                BitcoinHistoricalData.data == row['Date'].date()
            ).first()

            if not existing:
                record = BitcoinHistoricalData(
                    data=row['Date'].date(),
                    preco_eur=Decimal(str(row['Price'])),
                    volume=None,  # CSV doesn't have volume
                    market_cap=None
                )
                db.add(record)
                count += 1

        db.commit()
        print(f"✅ Inserted {count} new records into database")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


async def fetch_coingecko_data(days: int = 1825):
    """
    Fetch additional data from CoinGecko API

    Args:
        days: Number of days to fetch (default: 5 years)
    """
    print(f"\n🌐 Fetching {days} days from CoinGecko API...")

    updater = BitcoinUpdater()
    result = await updater.populate_historical(days)

    if result['success']:
        print(f"✅ Success! Processed {result['records_processed']} records")
        print(f"📅 Date range: {result['date_range']['from']} to {result['date_range']['to']}")
    else:
        print(f"❌ Error: {result['error']}")


def check_database():
    """
    Check current state of database
    """
    print("\n📊 Database Statistics:")

    db = SessionLocal()
    try:
        total = db.query(BitcoinHistoricalData).count()
        print(f"   Total records: {total}")

        if total > 0:
            oldest = db.query(BitcoinHistoricalData).order_by(
                BitcoinHistoricalData.data.asc()
            ).first()
            newest = db.query(BitcoinHistoricalData).order_by(
                BitcoinHistoricalData.data.desc()
            ).first()

            print(f"   Oldest date: {oldest.data}")
            print(f"   Newest date: {newest.data}")
            print(f"   Latest price: {newest.preco_eur} EUR")

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Bitcoin Data Population Script")
    print("=" * 50)

    # Path to CSV file
    csv_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'BTC_EUR Kraken Historical Data (1).csv'
    )

    # Check if CSV exists
    if os.path.exists(csv_path):
        load_csv_data(csv_path)
    else:
        print(f"⚠️  CSV file not found at {csv_path}")
        print("Skipping CSV import...")

    # Fetch data from CoinGecko
    print("\nFetching additional data from CoinGecko...")
    print("(This may take a minute...)")
    asyncio.run(fetch_coingecko_data(1825))  # 5 years

    # Show final statistics
    check_database()

    print("\n" + "=" * 50)
    print("✅ Bitcoin data population complete!")
    print("=" * 50)