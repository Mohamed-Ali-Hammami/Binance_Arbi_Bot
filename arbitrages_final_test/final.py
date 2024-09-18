import asyncio
import json
import websockets
import logging
import sqlite3
from sqlite3 import Error
import os
from flask_socketio import SocketIO

WEBSOCKET_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"
RECONNECT_INTERVAL = 5  # seconds
DB_FILE = 'c:\sqlite3\websocket_db_data.db'
print("Current working directory:", os.getcwd())

logging.basicConfig(level=logging.INFO)

# Create a database connection
connection = sqlite3.connect(DB_FILE)

async def websocket_handler(socket_io):
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            logging.info("WebSocket connection established.")
            parameters = {}  # Dictionary to store dynamic parameters
            while True:
                try:
                    response = await websocket.recv()
                    buffer = response
                    # Check if the buffer starts with '[' and ends with ']'
                    if buffer.startswith("[") and buffer.endswith("]"):
                        try:
                            # Parse the entire array
                            symbol_infos = json.loads(buffer)
                            # Emit data to Flask app
                            socket_io.emit('update_data', symbol_infos)
                            # Iterate over individual objects in the array
                            symbols_details = []
                            db_connection = create_connection()
                            symbol_info_manager = SymbolInfoManager()
                            semaphore = asyncio.Semaphore(1)
                            for symbol_info in symbol_infos:
                                bid_price = float(symbol_info.get('b'))
                                ask_price = float(symbol_info.get('a'))
                                volume = float(symbol_info.get('v'))
                                quote_volume = float(symbol_info.get('q'))
                                symbol_info_manager.add_symbol_info(symbol_info)
                                insert_symbol_info(db_connection, symbol_info)

                        except json.JSONDecodeError as json_error:
                            logging.error(f"Error decoding JSON array: {json_error}")
                except websockets.ConnectionClosedError as closed_error:
                    logging.error(f"WebSocket connection closed unexpectedly: {closed_error}")
                    break  # Break the inner loop and attempt to reconnect

                except Exception as e:
                    logging.error(f"Error in WebSocket connection: {e}")
                    # Sleep before attempting to reconnect
                    await asyncio.sleep(RECONNECT_INTERVAL)
    except Exception as e:
        logging.error(f"Error connecting to WebSocket: {e}")
        # Sleep before attempting to reconnect
        await asyncio.sleep(RECONNECT_INTERVAL)

class SymbolInfoManager:
    def __init__(self):
        self.symbol_infos = {}

    def add_symbol_info(self, symbol_info):
        symbol = symbol_info.get('s')
        bid_price = symbol_info.get('b', 0)
        ask_price = symbol_info.get('a', 0)
        volume = symbol_info.get('v', 0)
        quote_volume = symbol_info.get('q', 0)

        # Check if the symbol already exists in the dictionary
        if symbol in self.symbol_infos:
            # Update the existing entry
            self.symbol_infos[symbol] = {
                'bid_price': bid_price,
                'ask_price': ask_price,
                'volume': volume,
                'quote_volume': quote_volume
            }
        else:
            # Create a new entry for the symbol
            self.symbol_infos[symbol] = {
                'bid_price': bid_price,
                'ask_price': ask_price,
                'volume': volume,
                'quote_volume': quote_volume
            }

    def get_symbol_info(self, symbol):
        # Retrieve information for a specific symbol
        return self.symbol_infos.get(symbol)

def create_connection():
    try:
        connection = sqlite3.connect(os.path.abspath(DB_FILE))
        print(f"Connected to the database: {os.path.abspath(DB_FILE)}")
        return connection
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None

def insert_symbol_info(connection, symbol_info):
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO symbol_info (symbol, bid_price, ask_price, volume, quote_volume)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol_info['s'], float(symbol_info['b']), float(symbol_info['a']), float(symbol_info.get('v', 0)),
              float(symbol_info.get('q', 0))))
        connection.commit()
    except Error as e:
        print(f"Error inserting data into the database: {e}")

if __name__ == "__main__":
    # Reopen the database connection
    db_connection = create_connection()

    # Initialize SocketIO
    socket_io = SocketIO(async_mode='threading')
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(websocket_handler(socket_io))
    finally:
        # Close the database connection after the WebSocket handler completes
        if db_connection:
            db_connection.close()
