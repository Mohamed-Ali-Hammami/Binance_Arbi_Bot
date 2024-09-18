import pandas as pd
import asyncio
import aiohttp
import json

BINANCE_API_URL = "https://testnet.binance.vision/api/v3/exchangeInfo"
# Binance API endpoint for ticker data
TICKER_API_URL = "https://testnet.binance.vision/api/v3/ticker/bookTicker"


class BinanceAuth:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __call__(self, request):
        request.headers.update({
            'X-MBX-APIKEY': self.api_key,
        })
        return request

def read_config(file_path='arbitrages/config.json'):
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            api_key = data['API_KEYS']['API_KEY']
            secret_key = data['API_KEYS']['API_SECRET']
            return BinanceAuth(api_key, secret_key)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"Error reading configuration: {e}")
        return None

auth = read_config()
if auth:
    print("Authentication successful.")
else:
    print("Failed to obtain authentication credentials.")

async def fetch_binance_symbols_with_details(session):
    try:
        async with session.get(BINANCE_API_URL) as response_info:
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

                print(f"Selected {len(symbols_with_details)} symbols based on limit.")
                return symbols_with_details
            else:
                print("Error: 'symbols' key not found in the response.")
                return []
    except aiohttp.ClientError as ce:
        print(f"AIOHTTP ClientError: {ce}")
        return []
    except asyncio.TimeoutError:
        print("TimeoutError: The request timed out.")
        return []
    except Exception as e:
        print(f"Error fetching Binance symbols: {e}")
        return []

async def fetch_price_with_details(session, exchange, symbol, symbol_details_map):
    url_ticker = f"{TICKER_API_URL}?symbol={symbol}"
    try:
        async with session.get(url_ticker) as response_ticker:
            response_ticker.raise_for_status()
            ticker = await response_ticker.json()
            if ticker and 'bidPrice' in ticker:
                # Use symbol directly as key
                symbol_details = symbol_details_map.get(symbol, {})
                base_asset_precision = symbol_details.get('baseAssetPrecision', 0)
                quote_asset_precision = symbol_details.get('quoteAssetPrecision', 0)
                status = symbol_details.get('status', '')

                return (
                    (exchange['name'], symbol),
                    {
                        'ask': float(ticker['askPrice']),
                        'bid': float(ticker['bidPrice']),
                        'fee': exchange['fees']['trading']['taker'],
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


async def fetch_prices_with_details(session, exchanges, symbols):
    prices = {}

    symbol_details_map = await fetch_binance_symbols_with_details(session)

    tasks = [fetch_price_with_details(session, exchange, symbol, symbol_details_map) for exchange in exchanges for symbol in symbols]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            key = result[0]
            prices[key] = result[1]

    print("Finished fetching prices and symbols.")
    return prices

def compute_gain(ask, symbol, bid, fee_percentage, ask_volume, bid_volume, amount_in_dollars=100, slippage=0.001, network_fee=0.001, order_book_depth=100):
    try:
        adjusted_ask = float(ask) * (1 + slippage)
        adjusted_bid = float(bid) * (1 - slippage)

        if adjusted_ask <= 0 or adjusted_bid <= 0:
            raise ValueError(f"Invalid adjusted_ask or adjusted_bid for symbol {symbol}")

        amount = amount_in_dollars / float(ask)

        fee = max(float(ask) * float(ask_volume) * fee_percentage, float(bid) * float(bid_volume) * fee_percentage)

        actual_buy_price = adjusted_ask + network_fee
        actual_sell_price = adjusted_bid - network_fee

        net_gain_in_dollars = (actual_sell_price - actual_buy_price) * amount - fee

        return net_gain_in_dollars, amount_in_dollars + net_gain_in_dollars, fee, actual_sell_price, amount

    except (ValueError, TypeError) as e:
        print(f"Error calculating gain for symbol {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error calculating gain for symbol {symbol}: {e}")
        return None
    
def calculate_gains(row, amount):
    exchange = row['exchange']
    symbol = row['symbol']
    ask = row['ask']
    bid = row['bid']
    ask_volume = row['ask_volume']
    bid_volume = row['bid_volume']
    fee = row['fee']

    if ask <= bid:
        return pd.Series({'exchange': exchange, 'symbol': symbol, 'ask': ask, 'bid': bid, 'gain': None,
                          'gain_in_amount': None, 'buy_fee': None, 'sell_fee': None})

    buy_amount = amount
    buy_fee = buy_amount * fee
    sell_amount = buy_amount * bid
    sell_fee = sell_amount * fee
    gain = sell_amount - buy_amount - buy_fee - sell_fee
    remaining_amount = 0
    if gain > 0:
        # Calculate new remaining amount after successful trade
        remaining_amount = amount + gain
        return pd.Series({'exchange': exchange, 'symbol': symbol, 'ask': ask, 'bid': bid, 'gain': gain,
                          'gain_in_amount': amount, 'buy_fee': buy_fee, 'sell_fee': sell_fee,
                          'remaining_amount': remaining_amount})
    else:
        # No gain, return remaining amount
        return pd.Series({'exchange': exchange, 'symbol': symbol, 'ask': ask, 'bid': bid, 'gain': None,
                          'gain_in_amount': None, 'buy_fee': None, 'sell_fee': None, 'remaining_amount': remaining_amount}) 
        

async def find_arbitrage_opportunity(prices):
    print("Analyzing for arbitrage opportunities...")
    # Extract data for opportunities
    opportunities_data = [{'exchange': exchange, 'symbol': symbol, 'ask': data['ask'], 'bid': data['bid'],
                           'ask_volume': data['ask_volume'], 'bid_volume': data['bid_volume'], 'fee': data['fee']}
                          for (exchange, symbol), data in prices.items()]
    # Create DataFrame with opportunities data
    prices_df = pd.DataFrame(opportunities_data)
    # Filter out rows with non-positive ask_volume and bid_volume // ask volume & ask volume > 0 // bid volume & bid volume > 0
    prices_df = prices_df[(prices_df['ask_volume'].notnull()) & (prices_df['ask_volume'] > 0)]
    prices_df = prices_df[(prices_df['bid_volume'].notnull()) & (prices_df['bid_volume'] > 0)]
    # Print relevant columns
    print(prices_df[['exchange', 'symbol', 'ask', 'bid', 'ask_volume', 'bid_volume', 'fee']])
    # Calculate gains and add new columns using apply
    prices_df = prices_df.apply(calculate_gains, amount=100, axis=1)
    # Drop rows where gains_df is None (no arbitrage opportunity) 
    prices_df = prices_df.dropna()
    # Calculate net gain// net gain = gain- buy fee - sell fee 
    prices_df['net_gain'] = prices_df['gain'] - prices_df['buy_fee'] - prices_df['sell_fee']
    # Filter out opportunities with negative net gain // net gain > 0 
    opportunities_df = prices_df[prices_df['net_gain'] > 0]
    # Sort by net gain
    opportunities_df = opportunities_df.sort_values(by=['net_gain'], ascending=False)
    print("Arbitrage opportunities:")
    if not opportunities_df.empty:
        print(opportunities_df[['exchange', 'symbol', 'ask', 'bid', 'net_gain']])
    else:
        print("No arbitrage opportunities found.")
    

async def run():
    EXCHANGES = [
        {'name': 'Binance', 'fees': {'trading': {'taker': 0.001, 'maker': 0.001}}}
    ]

    async with aiohttp.ClientSession() as session:
        all_binance_symbols = await fetch_binance_symbols_with_details(session)
        SYMBOLS = list(all_binance_symbols.keys())

    if SYMBOLS:
        remaining_amount = 100  # Initial investment amount
        prices = await fetch_prices_with_details(session, SYMBOLS, all_binance_symbols)
        await find_arbitrage_opportunity(prices, remaining_amount)
    else:
        print("No symbols to process. Exiting...")

if __name__ == "__main__":
    asyncio.run(run())
