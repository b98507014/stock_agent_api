#!/usr/bin/env python3
"""
Railway build script to preload basic stock data
This runs during the build phase to ensure we have some data
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import random

def create_sample_data():
    """Create sample stock data for testing when real data is unavailable"""
    print("Creating sample stock data for Railway deployment...")

    # Create stock_data directory
    os.makedirs('stock_data', exist_ok=True)

    # Sample stocks
    stocks = ['2330', '2454', '2317', '3008', '2881']

    # Generate 3 months of sample data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    for stock in stocks:
        dates = []
        current_date = start_date

        data = []
        base_price = 100 + random.randint(0, 500)  # Random base price

        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday
                # Generate realistic price movements
                change = random.uniform(-0.05, 0.05)  # -5% to +5%
                open_price = base_price * (1 + change)
                high_price = open_price * (1 + random.uniform(0, 0.03))
                low_price = open_price * (1 - random.uniform(0, 0.03))
                close_price = random.uniform(low_price, high_price)
                volume = random.randint(1000000, 10000000)

                data.append({
                    'Date': current_date.strftime('%Y-%m-%d'),
                    'Open': round(open_price, 2),
                    'High': round(high_price, 2),
                    'Low': round(low_price, 2),
                    'Close': round(close_price, 2),
                    'Volume': volume
                })

                base_price = close_price  # Next day starts from previous close

            current_date += timedelta(days=1)

        # Save to CSV
        df = pd.DataFrame(data)
        df.to_csv(f'stock_data/{stock}.csv', index=False)
        print(f"Created sample data for {stock}: {len(df)} records")

    print("Sample data creation complete")

if __name__ == "__main__":
    create_sample_data()