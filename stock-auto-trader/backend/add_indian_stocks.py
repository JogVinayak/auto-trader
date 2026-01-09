#!/usr/bin/env python3
"""
Script to add popular Indian stocks from BSE and NSE
"""
import requests

API_BASE = "http://localhost:8000"

# Popular Indian stocks with NSE symbols (Yahoo Finance format)
INDIAN_STOCKS = [
    # Large Cap - IT
    ("TCS.NS", "Tata Consultancy Services"),
    ("INFY.NS", "Infosys"),
    ("WIPRO.NS", "Wipro"),
    ("HCLTECH.NS", "HCL Technologies"),
    ("TECHM.NS", "Tech Mahindra"),

    # Large Cap - Banking & Finance
    ("HDFCBANK.NS", "HDFC Bank"),
    ("ICICIBANK.NS", "ICICI Bank"),
    ("SBIN.NS", "State Bank of India"),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank"),
    ("AXISBANK.NS", "Axis Bank"),

    # Large Cap - Energy & Oil
    ("RELIANCE.NS", "Reliance Industries"),
    ("ONGC.NS", "Oil and Natural Gas Corporation"),
    ("IOC.NS", "Indian Oil Corporation"),
    ("BPCL.NS", "Bharat Petroleum"),

    # Large Cap - Auto
    ("TATAMOTORS.NS", "Tata Motors"),
    ("MARUTI.NS", "Maruti Suzuki"),
    ("M&M.NS", "Mahindra & Mahindra"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto"),

    # Large Cap - FMCG
    ("HINDUNILVR.NS", "Hindustan Unilever"),
    ("ITC.NS", "ITC Limited"),
    ("NESTLEIND.NS", "Nestle India"),
    ("BRITANNIA.NS", "Britannia Industries"),

    # Large Cap - Pharma
    ("SUNPHARMA.NS", "Sun Pharmaceutical"),
    ("DRREDDY.NS", "Dr. Reddy's Laboratories"),
    ("CIPLA.NS", "Cipla"),
    ("DIVISLAB.NS", "Divi's Laboratories"),

    # Large Cap - Metals
    ("TATASTEEL.NS", "Tata Steel"),
    ("HINDALCO.NS", "Hindalco Industries"),
    ("JSWSTEEL.NS", "JSW Steel"),
    ("VEDL.NS", "Vedanta Limited"),

    # Large Cap - Telecom & Infrastructure
    ("BHARTIARTL.NS", "Bharti Airtel"),
    ("LT.NS", "Larsen & Toubro"),
    ("POWERGRID.NS", "Power Grid Corporation"),

    # Large Cap - Consumer
    ("TITAN.NS", "Titan Company"),
    ("ASIANPAINT.NS", "Asian Paints"),
    ("ULTRACEMCO.NS", "UltraTech Cement"),
]

def add_stock(symbol, name):
    """Add a stock to the database"""
    try:
        response = requests.post(
            f"{API_BASE}/stocks",
            params={"symbol": symbol, "name": name}
        )
        if response.status_code == 200:
            print(f"✅ Added: {symbol} - {name}")
            return True
        else:
            print(f"❌ Failed to add {symbol}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error adding {symbol}: {e}")
        return False

def main():
    print("Adding Indian stocks to database...")
    print(f"Total stocks to add: {len(INDIAN_STOCKS)}\n")

    success_count = 0
    for symbol, name in INDIAN_STOCKS:
        if add_stock(symbol, name):
            success_count += 1

    print(f"\n✅ Successfully added {success_count}/{len(INDIAN_STOCKS)} stocks")

if __name__ == "__main__":
    main()
