import csv
from datetime import datetime
from pathlib import Path

# Portuguese month names mapping
PORTUGUESE_MONTHS = {
    'janeiro': 1,
    'fevereiro': 2,
    'março': 3,
    'abril': 4,
    'maio': 5,
    'junho': 6,
    'julho': 7,
    'agosto': 8,
    'setembro': 9,
    'outubro': 10,
    'novembro': 11,
    'dezembro': 12
}

def parse_portuguese_date(date_str):
    """
    Parse Portuguese date format like '5 de janeiro de 2022'
    Returns datetime object
    """
    parts = date_str.strip().split()
    day = int(parts[0])
    month_name = parts[2]
    year = int(parts[4])
    month = PORTUGUESE_MONTHS[month_name]
    return datetime(year, month, day)

def parse_btc_date(date_str):
    """
    Parse MM/DD/YYYY format
    Returns datetime object
    """
    return datetime.strptime(date_str.strip(), '%m/%d/%Y')

def parse_btc_price(price_str):
    """
    Parse price with comma as thousands separator like '94,536.6'
    Returns float
    """
    return float(price_str.replace(',', ''))

def find_closest_btc_price(target_date, btc_data):
    """
    Find the closest Bitcoin price for a given date
    btc_data is a list of (datetime, price) tuples
    """
    closest_date = None
    closest_price = None
    min_diff = None

    for btc_date, btc_price in btc_data:
        diff = abs((target_date - btc_date).days)
        if min_diff is None or diff < min_diff:
            min_diff = diff
            closest_date = btc_date
            closest_price = btc_price

    return closest_price

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    food_basket_file = script_dir / 'infogram_data_complete.csv'
    btc_file = script_dir / 'BTC_EUR Kraken Historical Data_daily.csv'
    output_file = script_dir / 'infogram_data_with_btc.csv'

    # Read Bitcoin data
    print("Reading Bitcoin price data...")
    btc_data = []
    with open(btc_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                btc_date = parse_btc_date(row['Date'])
                btc_price = parse_btc_price(row['Price'])
                btc_data.append((btc_date, btc_price))
            except (ValueError, KeyError) as e:
                print(f"Skipping Bitcoin row due to error: {e}")
                continue

    print(f"Loaded {len(btc_data)} Bitcoin price records")

    # Read food basket data and merge with Bitcoin prices
    print("Reading food basket data and merging with Bitcoin prices...")
    output_rows = []

    with open(food_basket_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Skip empty rows
                if not row['Date'] or not row['Price']:
                    continue

                # Parse food basket data
                food_date = parse_portuguese_date(row['Date'])
                food_price_eur = float(row['Price'])

                # Find closest Bitcoin price
                btc_price_eur = find_closest_btc_price(food_date, btc_data)

                if btc_price_eur:
                    # Calculate price in BTC
                    price_in_btc = food_price_eur / btc_price_eur

                    output_rows.append({
                        'Date': row['Date'],
                        'Price': food_price_eur,
                        'BTC_Price_EUR': btc_price_eur,
                        'Price_in_BTC': price_in_btc
                    })

                    print(f"{row['Date']}: Food basket €{food_price_eur:.2f}, BTC €{btc_price_eur:.2f}, In BTC: {price_in_btc:.8f}")
                else:
                    print(f"Warning: No Bitcoin price found for {row['Date']}")

            except (ValueError, KeyError) as e:
                print(f"Skipping food basket row due to error: {e}")
                continue

    # Write output file
    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Date', 'Price', 'BTC_Price_EUR', 'Price_in_BTC']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Successfully created {output_file}")
    print(f"Processed {len(output_rows)} records")

if __name__ == '__main__':
    main()
