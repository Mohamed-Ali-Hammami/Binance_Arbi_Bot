import aiohttp
import asyncio
import hmac
import hashlib
import json
import time
from Binance_auth import BinanceAuth
from urllib.parse import urlencode
import pandas as pd
from compute_gains import calculate_gains
import websockets


# Binance WebSocket URL for ticker updates
WEBSOCKET_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"

BINANCE_API_URL = "https://api.binance.com/api/v3/exchangeInfo"
# Binance API endpoint for ticker data
TICKER_API_URL = "https://api.binance.com/api/v3/ticker/bookTicker"

FEE_TABLE = {
    'VIP_0': 0.001,  # Adjust the fee percentages accordingly
    'VIP_1': 0.0009,
    # Add more fee tiers as needed
}

async def websocket_handler(prices):
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        while True:
            try:
                response = await websocket.recv()
                ticker_data = json.loads(response)
                # Process the ticker data and update prices dictionary
                # Your logic to update prices dictionary with new ticker data

                # Call find_arbitrage_opportunity with the updated prices
                await find_arbitrage_opportunity(prices)
                
            except Exception as e:
                print(f"Error in WebSocket connection: {e}")

async def fetch_account_info(session, api_key, secret_key):
    try:
        timestamp = str(int(time.time() * 1000))
        query_params = {'recvWindow': '5000', 'timestamp': timestamp}
        signature = generate_signature(secret_key, urlencode(query_params))

        headers = {
            'X-MBX-APIKEY': api_key,
        }

        query_params['signature'] = signature

        async with session.get("https://api.binance.com/api/v3/account", headers=headers, params=query_params) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error fetching account info: {response.status} - {response.reason}")
                print(f"Response content: {await response.text()}")
                return {}
    except aiohttp.ClientError as ce:
        print(f"AIOHTTP ClientError: {ce}")
        return {}
    except asyncio.TimeoutError:
        print("TimeoutError: The request timed out.")
        return {}
    except Exception as e:
        print(f"Error fetching Binance account info: {e}")
        return {}

def generate_signature(api_secret, data):
    signature = hmac.new(api_secret.encode(), data.encode(), digestmod=hashlib.sha256).hexdigest()
    return signature

def read_config(file_path=r'arbitrages\config.json'):
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            api_key = data['API_KEYS']['API_KEY']
            secret_key = data['API_KEYS']['API_SECRET']
            return api_key, secret_key
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"Error reading configuration: {e}")
        return None

async def fetch_binance_symbols_with_details(session, auth):
    try:
        if auth is None:
            print("Warning: BinanceAuth object is None. Using default values.")
            return {}, 'VIP_0'  # Return default values

        # Use the BinanceAuth object for authentication
        headers = {'X-MBX-APIKEY': auth.api_key}
        
        async with session.get(BINANCE_API_URL, headers=headers) as response_info:
            response_info.raise_for_status()
            exchange_info = await response_info.json()

            if 'symbols' in exchange_info:
                symbols = exchange_info['symbols']
                symbols_with_details = {
                    symbol['symbol']: {
                        'baseAsset': symbol.get('baseAsset', ''),
                        'quoteAsset': symbol.get('quoteAsset', ''),
                        'status': symbol.get('status', ''),
                        'baseAssetPrecision': symbol.get('baseAssetPrecision', 0),
                        'quoteAssetPrecision': symbol.get('quoteAssetPrecision', 0),
                    }
                    for symbol in symbols
                }

                # Retrieve fee tier information
                account_info = await fetch_account_info(session, auth.api_key, auth.secret_key)  # Fetch account info here
                fee_tier = account_info['feeTier'] if 'feeTier' in account_info else 'VIP_0'  # Use the fetched fee tier

                print(f"Selected {len(symbols_with_details)} symbols based on limit.")
                return symbols_with_details, fee_tier
            else:
                print("Error: 'symbols' key not found in the response.")
                return {}, 'VIP_0'  # Return default values

    except aiohttp.ClientError as ce:
        print(f"AIOHTTP ClientError: {ce}")
        return {}, 'VIP_0'  # Return default values
    except asyncio.TimeoutError:
        print("TimeoutError: The request timed out.")
        return {}, 'VIP_0'  # Return default values
    except Exception as e:
        print(f"Error fetching Binance symbols: {e}")
        return {}, 'VIP_0'  # Return default values
    
async def fetch_prices_with_details(session, exchanges, symbols, fee_tier, auth):
    prices = {}
    
    symbols_with_details, fee_tier = await fetch_binance_symbols_with_details(session, auth)

    tasks = [fetch_price_with_details(session, exchange, symbol, symbols_with_details, fee_tier) for exchange in exchanges for symbol in symbols]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            key = result[0]
            prices[key] = result[1]

    print("Finished fetching prices and symbols.")
    return prices

async def fetch_price_with_details(session, exchange, symbol, symbol_details_map, fee_tier):
    url_ticker = f"{TICKER_API_URL}?symbol={symbol}"
    try:
        async with session.get(url_ticker) as response_ticker:
            response_ticker.raise_for_status()
            ticker = await response_ticker.json()
            if ticker and 'bidPrice' in ticker:
                symbol_details = symbol_details_map.get(symbol, {})
                base_asset_precision = symbol_details.get('baseAssetPrecision', 0)
                quote_asset_precision = symbol_details.get('quoteAssetPrecision', 0)
                status = symbol_details.get('status', '')

                return (
                    (exchange['name'], symbol),
                    {
                        'ask': float(ticker['askPrice']),
                        'bid': float(ticker['bidPrice']),
                        'taker_fee': FEE_TABLE[fee_tier],  # Update this line
                        'ask_volume': float(ticker['askQty']),
                        'bid_volume': float(ticker['bidQty']),
                        'base_asset_precision': base_asset_precision,
                        'quote_asset_precision': quote_asset_precision,
                        'status': status
                    }
                )
            else:
                print(f"Invalid ticker data from {exchange['name']} for symbol {symbol}: {ticker}")

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Error fetching data for symbol {symbol} from {exchange['name']}: {e}")
        return None

async def find_arbitrage_opportunity(prices):
    print("Analyzing for arbitrage opportunities...")
    # Extract data for opportunities
    opportunities_data = [{'exchange': exchange, 'symbol': symbol, 'ask': data['ask'], 'bid': data['bid'],
                           'ask_volume': data['ask_volume'], 'bid_volume': data['bid_volume'], 'taker_fee': data['taker_fee']}
                          for (exchange, symbol), data in prices.items()]
    # Create DataFrame with opportunities data
    prices_df = pd.DataFrame(opportunities_data)
    # Filter out rows with non-positive ask_volume and bid_volume
    prices_df = prices_df[(prices_df['ask_volume'].notnull()) & (prices_df['ask_volume'] > 0)]
    prices_df = prices_df[(prices_df['bid_volume'].notnull()) & (prices_df['bid_volume'] > 0)]
    # Print relevant columns
    print(prices_df[['exchange', 'symbol', 'ask', 'bid', 'ask_volume', 'bid_volume', 'taker_fee']])
    # Calculate gains and add new columns using apply
    prices_df = prices_df.apply(calculate_gains, amount=100, axis=1)
    # Drop rows where gains_df is None (no arbitrage opportunity)
    prices_df = prices_df.dropna()
    # Calculate net gain
    prices_df['net_gain'] = prices_df['gain'] - prices_df['buy_fee'] - prices_df['sell_fee']
    # Filter out opportunities with negative net gain
    opportunities_df = prices_df[prices_df['net_gain'] > 0]
    # Sort by net gain
    opportunities_df = opportunities_df.sort_values(by=['net_gain'], ascending=False)
    print("Arbitrage opportunities:")
    if not opportunities_df.empty:
        print(opportunities_df[['exchange', 'symbol', 'ask', 'bid', 'net_gain']])
    else:
        print("No arbitrage opportunities found.")
    print("Finding arbitrage opportunities...")

    # Iterate through each symbol
    for symbol, symbol_data in prices.items():
        if isinstance(symbol_data, dict):  # Check if symbol_data is a dictionary
            # Iterate through each exchange
            for exchange_name, exchange_data in symbol_data.items():
                # Check if exchange_data is a dictionary
                if isinstance(exchange_data, dict):
                    ask_price = exchange_data.get('ask')
                    bid_price = exchange_data.get('bid')
                    taker_fee = exchange_data.get('taker_fee')
                    base_asset_precision = exchange_data.get('base_asset_precision')
                    quote_asset_precision = exchange_data.get('quote_asset_precision')

                    if ask_price > bid_price:
                        # Calculate the potential gain without fees
                        potential_gain = (1 / bid_price) * ask_price

                        # Apply taker fee
                        potential_gain -= taker_fee

                        # Convert potential gain to percentage
                        potential_gain_percentage = (potential_gain - 1) * 100

                        print(f"Arbitrage opportunity found on {exchange_name} for symbol {symbol}:")
                        print(f"Ask Price: {ask_price:.{quote_asset_precision}f}")
                        print(f"Bid Price: {bid_price:.{quote_asset_precision}f}")
                        print(f"Potential Gain: {potential_gain_percentage:.2f}%")
                        print()
    else:
            print('No arbitrage opportunity found')

    print("Finished finding opportunities.")



async def main():
    config = read_config()
    if config:
        api_key, secret_key = config
        async with aiohttp.ClientSession() as session:
            # Fetch Binance symbols with details
            binance_auth = BinanceAuth(api_key, secret_key)
            symbols_with_details, fee_tier = await fetch_binance_symbols_with_details(binance_auth)
            # Fetch account information
            account_info = await fetch_account_info(session, api_key, secret_key)
            print("Account info accessed successfully")
            
            # Start the WebSocket handler in the background
            asyncio.create_task(websocket_handler(prices))

            # Fetch Binance symbols with details
            binance_auth = BinanceAuth(api_key, secret_key)
            # Fetch prices with details for Binance
            binance_exchange = [{'name': 'Binance'}]
            
            # Move this line to a position before it is used
            symbols_with_details, fee_tier = await fetch_binance_symbols_with_details(session, binance_auth)
            
            symbols = list(symbols_with_details.keys())
            prices = await fetch_prices_with_details(session, binance_exchange, symbols, fee_tier, binance_auth)

            # Call find_arbitrage_opportunity with the obtained prices
            await find_arbitrage_opportunity(prices)
            
            # The rest of your code

    else:
        print("Failed to read configuration file.")

if __name__ == "__main__":
    asyncio.run(main())

