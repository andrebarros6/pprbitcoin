"""
Master script to setup and populate entire database
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from populate_pprs import populate_pprs, list_pprs
from populate_bitcoin import load_csv_data, fetch_coingecko_data, check_database
import asyncio


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


async def main():
    """
    Main setup function
    """
    print_header("PPR BITCOIN - DATABASE SETUP")

    # Step 1: Populate PPRs
    print_header("STEP 1: Populate PPRs")
    try:
        populate_pprs()
        list_pprs()
    except Exception as e:
        print(f"[ERROR] Error populating PPRs: {e}")
        return

    # Step 2: Populate Bitcoin data
    print_header("STEP 2: Populate Bitcoin Historical Data")

    # Try loading from CSV first
    csv_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'BTC_EUR Kraken Historical Data (1).csv'
    )

    if os.path.exists(csv_path):
        try:
            print("[CSV] Loading data from CSV...")
            load_csv_data(csv_path)
        except Exception as e:
            print(f"[WARNING] Error loading CSV: {e}")
    else:
        print(f"[WARNING] CSV file not found at {csv_path}")

    # Fetch from CoinGecko API
    try:
        print("\n[API] Fetching data from CoinGecko API...")
        print("   (This may take 1-2 minutes...)")
        await fetch_coingecko_data(1825)  # 5 years
    except Exception as e:
        print(f"[ERROR] Error fetching from CoinGecko: {e}")
        print("   Continuing without API data...")

    # Step 3: Populate PPR historical data
    print_header("STEP 3: Generate PPR Historical Data (Sample)")

    try:
        print("[DATA] Generating 5 years of sample historical data for PPRs...")
        print("   (This may take a minute...)")

        from populate_ppr_historical import populate_ppr_historical_data
        populate_ppr_historical_data(years=5)
    except Exception as e:
        print(f"[WARNING] Error generating PPR data: {e}")

    # Step 4: Show final statistics
    print_header("STEP 4: Database Statistics")
    check_database()

    # Final message
    print_header("[SUCCESS] DATABASE SETUP COMPLETE!")
    print("""
Next steps:
1. Start the API server:
   cd backend
   python app.py

2. Test the endpoints:
   http://localhost:8000/docs

3. Query the data:
   - GET /api/v1/pprs
   - GET /api/v1/bitcoin/historical
    """)


if __name__ == "__main__":
    asyncio.run(main())