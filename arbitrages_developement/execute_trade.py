import aiohttp
import asyncio
import time
from urllib.parse import urlencode
from fetch_info import generate_signature, read_config

async def execute_trade(session, auth, symbol, quantity, side, type, price):
    try:
        timestamp = str(int(time.time() * 1000))
        query_params = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'timeInForce': 'GTC',
            'quantity': quantity,
            'price': price,
            'timestamp': timestamp
        }

        signature = generate_signature(auth.secret_key, urlencode(query_params))

        headers = {
            'X-MBX-APIKEY': auth.api_key,
        }

        query_params['signature'] = signature

        async with session.post("https://testnet.binance.vision/api/v3/order", headers=headers, params=query_params) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error executing trade: {response.status} - {response.reason}")
                print(f"Response content: {await response.text()}")
                return None

    except aiohttp.ClientError as ce:
        print(f"AIOHTTP ClientError: {ce}")
        return None
    except asyncio.TimeoutError:
        print("TimeoutError: The request timed out.")
        return None
    except Exception as e:
        print(f"Error executing trade: {e}")
        return None

async def execute_opportunity(session, auth, opportunity):
    # Extract relevant information from the opportunity
    symbol = opportunity['symbol']
    ask = opportunity['ask']
    bid = opportunity['bid']
    net_gain = opportunity['net_gain']

    # Assuming you want to take the opportunity with a fixed quantity, you may need to adjust this based on your strategy
    quantity = 0.001  # Example quantity, adjust as needed

    # Simulate executing the trade
    print(f"Simulating executing the trade for symbol {symbol}...")
    await execute_trade(session, auth, symbol, quantity, 'BUY', 'LIMIT', bid)  # Buy at bid price
    await execute_trade(session, auth, symbol, quantity, 'SELL', 'LIMIT', ask)  # Sell at ask price

    # Simulate updating the remaining amount after the trade
    remaining_amount = 100 + net_gain
    print(f"New remaining amount after executing the trade: ${remaining_amount:.2f}")

async def main(opportunities_df, auth):
    # Read Binance API credentials from config file
    if auth:
        print("Authentication successful.")
        # Create a Binance client instance using BinanceAuth
        async with aiohttp.ClientSession() as session:
            # Iterate over rows in the opportunities DataFrame
            for index, opportunity in opportunities_df.iterrows():
                await execute_opportunity(session, auth, opportunity)
    else:
        print("Failed to obtain authentication credentials.")

if __name__ == "__main__":
    # Assuming you have the arbitrage opportunities DataFrame from arbitrage.py
    # You need to replace the following line with the actual DataFrame obtained from arbitrage.py
    opportunities_df = ...

    # Read Binance API credentials using fetch_info
    auth = read_config()

    if not opportunities_df.empty and auth:
        asyncio.run(main(opportunities_df, auth))
    else:
        print("No arbitrage opportunities found or failed to obtain authentication credentials.")
