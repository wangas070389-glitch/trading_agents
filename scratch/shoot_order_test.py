import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.alpaca_connector import AlpacaConnector

def main():
    connector = AlpacaConnector()
    
    print("Testing Alpaca Connection...")
    try:
        acct = connector.get_account_info()
        print("Successfully connected to Alpaca Account!")
        print(f"  Account ID:      {acct.get('id')}")
        print(f"  Account Status:  {acct.get('status')}")
        print(f"  Cash Balance:    ${float(acct.get('cash', 0.0)):,.2f} USD")
        print(f"  Buying Power:    ${float(acct.get('buying_power', 0.0)):,.2f} USD")
        print(f"  Portfolio Value: ${float(acct.get('portfolio_value', 0.0)):,.2f} USD")
    except Exception as e:
        print(f"Error connecting to account: {e}")
        return

    ticker = "AAPL"
    qty = 1
    side = "buy"
    
    print(f"\nSubmitting live test order: {side.upper()} {qty} share of {ticker}...")
    try:
        order = connector.submit_order(ticker=ticker, qty=qty, side=side)
        print("Order submitted successfully!")
        print(f"  Order ID:       {order.get('id')}")
        print(f"  Status:         {order.get('status')}")
        print(f"  Asset Class:    {order.get('asset_class')}")
        print(f"  Created At:     {order.get('created_at')}")
    except Exception as e:
        print(f"Error submitting order: {e}")

if __name__ == "__main__":
    main()
