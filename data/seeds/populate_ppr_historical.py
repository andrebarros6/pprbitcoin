"""
Script to populate PPR historical data with sample/demo data
For production, this would be replaced by actual scrapers
"""
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from database import SessionLocal
from models.ppr import PPR, PPRHistoricalData


def generate_sample_data(ppr: PPR, start_date: datetime, end_date: datetime, initial_value: Decimal):
    """
    Generate sample historical data for a PPR

    Args:
        ppr: PPR instance
        start_date: Start date for data
        end_date: End date for data
        initial_value: Initial quota value

    Returns:
        List of historical data records
    """
    records = []
    current_date = start_date
    current_value = initial_value

    # Different return profiles based on category
    if ppr.categoria == "Conservador":
        monthly_return_mean = 0.003  # ~3.6% annual
        monthly_return_std = 0.01  # Low volatility
    elif ppr.categoria == "Moderado":
        monthly_return_mean = 0.004  # ~4.8% annual
        monthly_return_std = 0.015  # Medium volatility
    else:  # Dinâmico
        monthly_return_mean = 0.006  # ~7.2% annual
        monthly_return_std = 0.025  # Higher volatility

    while current_date <= end_date:
        # Generate return with some randomness
        monthly_return = random.gauss(monthly_return_mean, monthly_return_std)
        current_value = current_value * Decimal(str(1 + monthly_return))

        records.append({
            "data": current_date.date(),
            "valor_quota": round(current_value, 4)
        })

        # Move to next month (first day)
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)

    return records


def populate_ppr_historical_data(years: int = 5):
    """
    Populate historical data for all PPRs

    Args:
        years: Number of years of historical data to generate
    """
    print("=" * 70)
    print("PPR Historical Data Population Script")
    print("=" * 70)

    db = SessionLocal()

    try:
        pprs = db.query(PPR).all()

        if not pprs:
            print("[ERROR] No PPRs found in database. Run populate_pprs.py first!")
            return

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        print(f"\nGenerating {years} years of historical data...")
        print(f"Date range: {start_date.date()} to {end_date.date()}\n")

        total_records = 0

        for ppr in pprs:
            # Set initial quota value based on category
            if ppr.categoria == "Conservador":
                initial_value = Decimal("5.0000")
            elif ppr.categoria == "Moderado":
                initial_value = Decimal("4.5000")
            else:  # Dinâmico
                initial_value = Decimal("4.0000")

            print(f"[DATA] {ppr.nome} ({ppr.categoria})...")

            # Generate sample data
            records = generate_sample_data(ppr, start_date, end_date, initial_value)

            # Save to database
            count = 0
            for record in records:
                # Check if already exists
                existing = db.query(PPRHistoricalData).filter(
                    PPRHistoricalData.ppr_id == ppr.id,
                    PPRHistoricalData.data == record['data']
                ).first()

                if not existing:
                    new_record = PPRHistoricalData(
                        ppr_id=ppr.id,
                        data=record['data'],
                        valor_quota=record['valor_quota']
                    )
                    db.add(new_record)
                    count += 1

            db.commit()
            total_records += count

            # Show summary
            final_value = records[-1]['valor_quota']
            total_return = ((final_value - initial_value) / initial_value) * 100
            print(f"   [OK] Added {count} records")
            print(f"   Initial: {initial_value} EUR → Final: {final_value} EUR")
            print(f"   Total return: {total_return:.2f}%\n")

        print("=" * 70)
        print(f"✅ Success! Added {total_records} total historical records")
        print("=" * 70)

        # Show statistics
        print("\n[STATS] Database Statistics:")
        for ppr in pprs:
            count = db.query(PPRHistoricalData).filter(
                PPRHistoricalData.ppr_id == ppr.id
            ).count()
            print(f"   {ppr.nome}: {count} records")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error: {e}")
        raise
    finally:
        db.close()


def show_sample_data():
    """
    Show sample data from database
    """
    db = SessionLocal()

    try:
        print("\n" + "=" * 70)
        print("Sample PPR Historical Data (Latest 3 records per PPR)")
        print("=" * 70)

        pprs = db.query(PPR).limit(3).all()

        for ppr in pprs:
            print(f"\n{ppr.nome}:")
            print("-" * 70)

            records = db.query(PPRHistoricalData).filter(
                PPRHistoricalData.ppr_id == ppr.id
            ).order_by(PPRHistoricalData.data.desc()).limit(3).all()

            if records:
                for record in records:
                    print(f"   {record.data}: {record.valor_quota} EUR")
            else:
                print("   No data available")

    finally:
        db.close()


if __name__ == "__main__":
    # Set seed for reproducibility
    random.seed(42)

    # Populate data
    populate_ppr_historical_data(years=5)

    # Show sample
    show_sample_data()

    print("\n" + "=" * 70)
    print("[WARNING]  NOTE: This is SAMPLE DATA for demonstration purposes")
    print("In production, this would be replaced by actual scraped data")
    print("=" * 70)