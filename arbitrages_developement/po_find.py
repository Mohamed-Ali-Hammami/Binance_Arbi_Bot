import asyncio
import ccxt
import json

WEBSOCKET_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"
RECONNECT_INTERVAL = 5  # seconds

API_KEY = "YOUR_BINANCE_API_KEY"
SECRET_KEY = "YOUR_BINANCE_SECRET_KEY"

async def get_trading_fee(exchange, symbol):
    try:
        # Fetch the trading fee for the specified symbol
        symbol_info = exchange.fetch_trading_fee(symbol)
        taker_fee = next(filter(lambda x: x['maker'] == 0 and x['symbol'] == symbol, symbol_info['info']['tradeFee']), None)

        if taker_fee:
            return taker_fee['taker']
        else:
            return None
    except ccxt.NetworkError as e:
        print(f"Network error in get_trading_fee: {e}")
        return None
    except ccxt.ExchangeError as e:
        print(f"Exchange error in get_trading_fee: {e}")
        return None

async def arbitrage_opportunity_finder():
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
    })

    while True:
        try:
            async with ccxt.async_support.websocket(WEBSOCKET_URL) as ws:
                print("WebSocket connection established.")
                while True:
                    try:
                        response = await ws.recv()
                        ticker_data = json.loads(response)

                        # Extract symbol, bid, and ask prices
                        symbol = ticker_data['s']
                        bid_price = float(ticker_data['b'])
                        ask_price = float(ticker_data['a'])

                        # Get trading fee for the specified symbol
                        symbol_fee = await get_trading_fee(exchange, symbol)
                        if symbol_fee is not None:
                            print(f"Taker fee for {symbol}: {symbol_fee}")

                        # Check for arbitrage opportunities
                        calculate_and_print_opportunity(symbol, bid_price, ask_price, symbol_fee)

                    except Exception as e:
                        print(f"Error in WebSocket connection: {e}")
                        # Sleep before attempting to reconnect
                        await asyncio.sleep(RECONNECT_INTERVAL)

        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")
            # Sleep before attempting to reconnect
            await asyncio.sleep(RECONNECT_INTERVAL)

async def calculate_and_print_opportunity(symbol, bid_price, ask_price, symbol_fee):
    # Set your slippage rate here (modify as needed)
    slippage_rate = 0.001  # 0.1% slippage

    # Calculate potential gain with fees and slippage
    potential_gain = (1 - symbol_fee) * (bid_price * (1 - slippage_rate) / ask_price) - 1

    print(f"Symbol: {symbol}, Bid Price: {bid_price}, Ask Price: {ask_price}, "
          f"Taker Fee: {symbol_fee}, Potential Gain: {potential_gain:.2%}")


# Example usage in the main function
async def main():
    await arbitrage_opportunity_finder()

if __name__ == "__main__":
    asyncio.run(main())
