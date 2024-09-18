import asyncio
import json
import websockets
import itertools
import requests

WEBSOCKET_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"
RECONNECT_INTERVAL = 1000  # seconds

API_KEY = "Your own"

async def websocket_handler():
    symbols_details = []
    buffer = ""  # Buffer to accumulate partial JSON data
    while True:
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                print("WebSocket connection established.")
                while True:
                    try:
                        response = await websocket.recv()
                        print(f"Received data: {response}")
                        buffer += response
                        # Split concatenated JSON objects
                        parts = buffer.split("}{")
                        for part in parts[:-1]:
                            part += "}"
                            try:
                                symbol_info = json.loads(part)
                            except json.JSONDecodeError as json_error:
                                print(f"Error decoding JSON: {json_error}")
                                continue  # Skip the rest of the loop iteration
                            # Extract details for each symbol
                            symbol = symbol_info.get('s', '')
                            if not symbol:
                                print("Error: Symbol not found in symbol_info.")
                                continue  # Skip the rest of the loop iteration

                            # Add symbol details to the list
                            symbols_details.append({
                                'symbol': symbol,
                                'bid_price': symbol_info.get('b', 0),
                                'ask_price': symbol_info.get('a', 0),
                            })

                            # Get trading fees for the specified symbol
                            symbol_fee = get_trading_fee(symbol)
                            if symbol_fee is not None:
                                print(f"Taker fee for {symbol}: {symbol_fee}")
                            else:
                                print(f"Taker fee not found for {symbol}")

                        buffer = parts[-1]  # Remaining partial JSON

                    except Exception as e:
                        print(f"Error in WebSocket connection: {e}")
                        # Sleep before attempting to reconnect
                        await asyncio.sleep(RECONNECT_INTERVAL)

        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")
            # Sleep before attempting to reconnect
            await asyncio.sleep(RECONNECT_INTERVAL)

        # Move the return statement outside the while loop
        return symbols_details




def calculate_potential_gain(symbol1_bid_price, symbol2_ask_price, symbol1_fee, symbol2_fee, slippage_rate):
    # Check if bid and ask prices are both positive
    if symbol1_bid_price > 0 and symbol2_ask_price > 0:
        # Calculate potential gain percentage
        potential_gain = ((symbol1_bid_price - symbol2_ask_price) / symbol2_ask_price) * 100

        # Apply slippage
        symbol1_bid_price *= (1 - slippage_rate)
        symbol2_ask_price *= (1 + slippage_rate)

        # Apply fees
        symbol1_bid_price /= (1 - symbol1_fee)
        symbol2_ask_price *= (1 + symbol2_fee)

        # Calculate potential gain
        potential_gain = (symbol1_bid_price / symbol2_ask_price) - 1

    return potential_gain


def find_arbitrage_opportunity(symbols_details):
    print("Analyzing for arbitrage opportunities...")
    # Create a list to store opportunities
    opportunities = []

    # Iterate through each combination of symbols
    for symbol1, symbol2 in itertools.combinations(symbols_details, 2):
        # Extract necessary details
        symbol1_bid_price = float(symbol1['bid_price'])
        symbol2_ask_price = float(symbol2['ask_price'])

        # Check for non-zero bid and ask prices
        if symbol1_bid_price > 0 and symbol2_ask_price > 0:
            # Set your fee and slippage rates here (modify as needed)
            fee_rate = 0.001  # 0.1% fee
            slippage_rate = 0.001  # 0.1% slippage

            # Calculate potential gain with fees and slippage
            potential_gain = calculate_potential_gain(symbol1_bid_price, symbol2_ask_price, fee_rate, slippage_rate)

            # Add opportunity to the list
            opportunities.append({
                'symbol1': symbol1['symbol'],
                'symbol2': symbol2['symbol'],
                'bid_price': symbol1_bid_price,
                'ask_price': symbol2_ask_price,
                'potential_gain': potential_gain
            })

    # Sort opportunities by potential gain
    opportunities = sorted(opportunities, key=lambda x: x['potential_gain'], reverse=True)

    print("Arbitrage opportunities:")
    if opportunities:
        for opportunity in opportunities:
            print(f"Symbol 1: {opportunity['symbol1']}, Symbol 2: {opportunity['symbol2']}, "
                  f"Bid Price: {opportunity['bid_price']}, Ask Price: {opportunity['ask_price']}, "
                  f"Potential Gain: {opportunity['potential_gain']:.2%}")
    else:
        print("No arbitrage opportunities found.")
    print("Finished finding opportunities.")

def get_trading_fee(symbol):
    try:
        print(f"Getting trading fee for symbol: {symbol}")
        endpoint = 'https://api.binance.com/api/v3/tradeFee'
        params = {'symbol': symbol}
        headers = {'X-MBX-APIKEY': API_KEY}
        response = requests.get(endpoint, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for bad responses
        data = response.json()

        # Find the taker fee for the specified symbol
        taker_fee = next(filter(lambda x: x['makerCommission'] == 0 and x['symbol'] == symbol, data), None)

        if taker_fee:
            print(f"Taker fee found for {symbol}: {taker_fee['takerCommission']}")
            return taker_fee['takerCommission']
        else:
            print(f"Taker fee not found for {symbol}")
            return None
    except requests.RequestException as e:
        print(f"Error in get_trading_fee: {e}")
        return None


# Example usage in the main function
async def main():
    while True:
        symbols_details = await websocket_handler()
        if symbols_details:
            find_arbitrage_opportunity(symbols_details)

if __name__ == "__main__":
    asyncio.run(main())
