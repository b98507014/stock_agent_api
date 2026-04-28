
import requests
import pandas as pd
import datetime
import os
import json

def fetch_stock_history(stock_code):
    """
    Fetches Taiwanese stock historical data from TWSE website and updates the local CSV file.
    Combines new data with existing data for AI training purposes.
    
    Args:
        stock_code (str): The stock code, e.g., '2330'
    
    Returns:
        pd.DataFrame: The updated DataFrame with historical stock data
    """
    data_dir = 'stock_data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    data_file = os.path.join(data_dir, f'{stock_code}.csv')
    
    if os.path.exists(data_file):
        df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        last_date = df.index.max().date() if not df.empty else datetime.date(2020, 1, 1)
    else:
        df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        last_date = datetime.date(2020, 1, 1)  # Default start date
    
    today = datetime.date.today()
    
    if last_date >= today:
        return df  # No new data to fetch
    
    # Function to convert ROC date to AD date
    def roc_to_ad(roc_date):
        try:
            year, month, day = map(int, roc_date.split('/'))
            ad_year = year + 1911
            return datetime.date(ad_year, month, day)
        except ValueError:
            return None
    
    new_data = []
    current = last_date.replace(day=1)  # Start from the beginning of the month after last_date
    
    while current <= today:
        date_str = current.strftime('%Y%m%d')
        url = f'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}'
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']:
                for row in data['data']:
                    date_roc = row[0]
                    date_ad = roc_to_ad(date_roc)
                    
                    if date_ad and date_ad > last_date and date_ad <= today:
                        try:
                            open_p = float(row[3].replace(',', ''))
                            high = float(row[4].replace(',', ''))
                            low = float(row[5].replace(',', ''))
                            close = float(row[6].replace(',', ''))
                            volume = int(row[1].replace(',', ''))
                            
                            new_data.append({
                                'Date': date_ad,
                                'Open': open_p,
                                'High': high,
                                'Low': low,
                                'Close': close,
                                'Volume': volume
                            })
                        except (ValueError, IndexError):
                            continue  # Skip invalid rows
        except requests.RequestException:
            continue  # Skip if request fails
        
        # Move to the next month
        current = (current + datetime.timedelta(days=32)).replace(day=1)
    
    if new_data:
        new_df = pd.DataFrame(new_data).set_index('Date')
        # Ensure consistent datetime index
        new_df.index = pd.to_datetime(new_df.index)
        df = pd.concat([df, new_df]).drop_duplicates().sort_index()
        df.to_csv(data_file)
    
    return df

def fetch_multiple_stocks(stock_codes=None):
    """
    Fetches historical data for multiple Taiwanese stocks.
    If stock_codes is None, uses a default diverse list of stocks.
    
    Args:
        stock_codes (list): List of stock codes, e.g., ['2330', '2454']
    
    Returns:
        dict: Dictionary with stock codes as keys and DataFrames as values
    """
    if stock_codes is None:
        # Default diverse list of Taiwanese stocks across industries
        stock_codes = [
            '2330',  # 台積電 (Semiconductor)
            '2454',  # 聯發科 (Semiconductor)
            '2317',  # 鴻海 (Electronics)
            '3008',  # 大立光 (Optics)
            '4938',  # 和碩 (Electronics)
            '2881',  # 富邦金 (Financial)
            '2882',  # 國泰金 (Financial)
            '1101',  # 台泥 (Cement)
            '2002',  # 中鋼 (Steel)
            '1301',  # 台塑 (Plastics)
            '1326',  # 台化 (Chemicals)
            '2603',  # 長榮 (Shipping)
            '2615',  # 萬海 (Shipping)
            '6505',  # 台塑化 (Petrochemical)
            '2412',  # 中華電 (Telecom)
            '3045',  # 台灣大哥大 (Telecom)
            '2891',  # 中信金 (Financial)
            '2886',  # 兆豐金 (Financial)
            '1216',  # 統一 (Food)
            '2912',  # 統一超 (Retail)
            '2357',  # 華碩 (Electronics)
            '2379',  # 瑞昱 (Semiconductor)
            '2382',  # 廣達 (Electronics)
            '2395',  # 研華 (Industrial)
            '3034',  # 聯詠 (Semiconductor)
        ]
    
    results = {}
    for code in stock_codes:
        print(f"Fetching data for stock {code}...")
        df = fetch_stock_history(code)
        results[code] = df
        print(f"Completed {code}: {len(df)} records")
    
    return results

# Example usage:
# results = fetch_multiple_stocks()
# for code, df in results.items():
#     print(f"{code}: {df.shape}")

if __name__ == "__main__":
    print("Starting to fetch data for 25 diverse Taiwanese stocks...")
    results = fetch_multiple_stocks()
    print("\nFetch completed! Summary:")
    total_records = 0
    for code, df in results.items():
        print(f"{code}: {len(df)} records")
        total_records += len(df)
    print(f"\nTotal records across all stocks: {total_records}")
    print("Data saved in 'stock_data/' directory as individual CSV files.")