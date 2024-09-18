import json
import asyncio
import websockets
import requests

API_KEY = "Your_API_Key_Here"

WEBSOCKET_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"
async def websocket_handler():
    symbols_details = []
    buffer = ""
    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            print("WebSocket connection established.")
            while True:
                try:
                    response = await ws.recv()
                    print(f"Received data: {response}")
                    buffer += response
                    parts = buffer.split("}{")
                    for part in parts[:-1]:
                        part += "}"
                        try:
                            symbol_info = json.loads(part)
                        except json.JSONDecodeError as json_error:
                            print(f"Error decoding JSON: {json_error}")
                            continue
                        symbol = symbol_info.get('s', '')
                        if not symbol:
                            print("Error: Symbol not found in symbol_info.")
                            continue
                        symbols_details.append({
                            'symbol': symbol,
                            'bid_price': symbol_info.get('b', 0),
                            'ask_price': symbol_info.get('a', 0),
                        })
                        # Replace this with your function to get trading fees for the symbol
                        symbol_fee = await get_trading_fee(symbol)
                        if symbol_fee is not None:
                            print(f"Taker fee for {symbol}: {symbol_fee}")
                        else:
                            print(f"Taker fee not found for {symbol}")

                    buffer = parts[-1]

                except Exception as e:
                    print(f"Error in WebSocket connection: {e}")
                    break  # Break the loop on error
    except Exception as e:
        print(f"Error connecting to WebSocket: {e}")

    return symbols_details

async def get_trading_fee(symbol):
    try:
        print(f"Getting trading fee for symbol: {symbol}")
        endpoint = 'https://api.binance.com/api/v3/tradeFee'
        params = {'symbol': symbol}
        headers = {'X-MBX-APIKEY': API_KEY}
        response = await requests.get(endpoint, params=params, headers=headers)
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

if __name__ == "__main__":
    asyncio.run(websocket_handler())
