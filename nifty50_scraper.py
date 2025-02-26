import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import os
from tqdm import tqdm

def create_data_directories():
    # Create both directories
    nifty50_dir = os.path.join(os.path.dirname(__file__), 'nifty_50')
    niftynext50_dir = os.path.join(os.path.dirname(__file__), 'nifty_next50')
    os.makedirs(nifty50_dir, exist_ok=True)
    os.makedirs(niftynext50_dir, exist_ok=True)
    return nifty50_dir, niftynext50_dir

def get_stock_symbols():
    # Read both NIFTY 50 and NIFTY NEXT 50 symbols
    nifty50_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'details_50.csv'))
    niftynext50_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'details_nxt50.csv'))
    
    # Add .NS suffix to symbols for NSE stocks
    nifty50_symbols = [f"{symbol}.NS" for symbol in nifty50_df['Symbol']]
    niftynext50_symbols = [f"{symbol}.NS" for symbol in niftynext50_df['Symbol']]
    
    return {
        'nifty50': (nifty50_symbols, nifty50_df['Company Name']),
        'niftynext50': (niftynext50_symbols, niftynext50_df['Company Name'])
    }

def scrape_stock_data(symbol, company_name, data_dir):
    # Set fixed start date to January 1, 2010
    start_date = datetime(2010, 1, 1)
    end_date = datetime.now()
    
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            return False
        
        # Process data
        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Save to CSV with organized structure
        clean_name = company_name.replace(' ', '_').replace('.', '').replace('&', 'and')
        filename = f"{clean_name}_{symbol.replace('.', '_')}.csv"
        filepath = os.path.join(data_dir, filename)
        df.to_csv(filepath, index=False)
        return True
        
    except Exception as e:
        print(f"\nError fetching data for {symbol}: {str(e)}")
        return False

def process_stock_list(symbols, companies, data_dir, list_name):
    print(f"\n=== {list_name} Data Collection Started ===")
    total_stocks = len(symbols)
    print(f"\nCollecting data for {total_stocks} stocks...")
    
    summary = {"success": [], "failed": []}
    
    for symbol, company in tqdm(zip(symbols, companies), total=total_stocks, desc=f"Processing {list_name}"):
        if scrape_stock_data(symbol, company, data_dir):
            summary["success"].append(f"{company} ({symbol})")
        else:
            summary["failed"].append(f"{company} ({symbol})")
    
    return summary

def print_summary(summary, list_name):
    total = len(summary["success"]) + len(summary["failed"])
    print(f"\n=== {list_name} Download Summary ===")
    print(f"Successfully downloaded: {len(summary['success'])}/{total}")
    print(f"Failed downloads: {len(summary['failed'])}")
    
    if summary["failed"]:
        print("\nFailed stocks:")
        for stock in summary["failed"]:
            print(f"- {stock}")

def main():
    nifty50_dir, niftynext50_dir = create_data_directories()
    stock_data = get_stock_symbols()
    
    # Process NIFTY 50
    nifty50_summary = process_stock_list(
        stock_data['nifty50'][0],
        stock_data['nifty50'][1],
        nifty50_dir,
        "NIFTY 50"
    )
    
    # Process NIFTY NEXT 50
    niftynext50_summary = process_stock_list(
        stock_data['niftynext50'][0],
        stock_data['niftynext50'][1],
        niftynext50_dir,
        "NIFTY NEXT 50"
    )
    
    # Print summaries
    print_summary(nifty50_summary, "NIFTY 50")
    print_summary(niftynext50_summary, "NIFTY NEXT 50")
    
    print("\nData collection completed!")
    print(f"NIFTY 50 files saved in: {os.path.abspath(nifty50_dir)}")
    print(f"NIFTY NEXT 50 files saved in: {os.path.abspath(niftynext50_dir)}")

if __name__ == "__main__":
    main()
