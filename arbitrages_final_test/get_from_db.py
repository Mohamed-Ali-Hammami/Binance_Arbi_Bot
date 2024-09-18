import sqlite3
from sqlite3 import Error
import os
import time

MINIMUM_LENGTH = 3
DB_FILE = 'c:\sqlite3\websocket_db_data.db'

def create_connection():
    try:
        connection = sqlite3.connect(os.path.abspath(DB_FILE))
        print(f"Connected to the database: {os.path.abspath(DB_FILE)}")
        return connection
    except Error as e:
        print(f"Error connecting to the database: {e}")
        return None
    
def calculate_gains_based_on_arbitrage(symbol, amount, ask_price, bid_price, slippage=0.001):
    # Buy at the bid price
    buy_amount = amount / bid_price
    # Account for slippage on the ask price
    effective_ask_price = ask_price * (1 + slippage)
    # Sell at the adjusted ask price 
    sell_amount = buy_amount * effective_ask_price
    # Calculate net gain  
    net_gain = float(sell_amount - amount)
    return {
        'symbol': symbol,
        'net_gain': net_gain
    }

def fetch_symbol_info(connection, second_symbol_in_pair):
    try:
        print(f"Executing SQL query: SELECT * FROM symbol_info WHERE symbol LIKE '{second_symbol_in_pair}%'")
        cursor = connection.cursor()

        while second_symbol_in_pair and len(second_symbol_in_pair) >= MINIMUM_LENGTH:
            cursor.execute("SELECT * FROM symbol_info WHERE symbol LIKE ?", (f"{second_symbol_in_pair}%",))
            rows = cursor.fetchall()

            calculated_gains_list = []  # List to store gains for each symbol

            for row in rows:
                # Calculate gains based on arbitrage
                symbol = row[0]
                bid_price = float(row[1])
                ask_price = float(row[2])
                gains_info = calculate_gains_based_on_arbitrage(symbol, 100, ask_price, bid_price)

                # Append gains_info to the list
                calculated_gains_list.append(gains_info)

            if calculated_gains_list:  # Check if the list is not empty
                # Find and return the symbol with the highest arbitrage gain
                highest_gain_symbol = max(calculated_gains_list, key=lambda gains_info: gains_info['net_gain'])
                symbol_pair = highest_gain_symbol['symbol']
                new_second_symbol_in_pair = symbol_pair[3:]
                return highest_gain_symbol, new_second_symbol_in_pair
            else:
                print(f"No matching symbols found for {second_symbol_in_pair}. Trying variations.")

            # If no matches found, try removing the first character
            second_symbol_in_pair = second_symbol_in_pair[1:]

            if not second_symbol_in_pair:
                break  # Break the loop if the string becomes empty

        print("No matching symbol found for variations.")
        return None, None
    except Error as e:
        print(f"Error fetching data from the database: {e}")



def fetch_symbol_info_with_second_symbol_in_pair(connection, second_symbol_in_pair):
    print(f"Executing SQL query: SELECT * FROM symbol_info WHERE symbol LIKE '{second_symbol_in_pair}%'")

    try:
        cursor = connection.cursor()

        while second_symbol_in_pair and len(second_symbol_in_pair) >= MINIMUM_LENGTH:
            # Modify the SQL query to fetch symbols starting with second_symbol_in_pair
            cursor.execute("SELECT * FROM symbol_info WHERE symbol LIKE ?", (f"{second_symbol_in_pair}%",))
            rows = cursor.fetchall()

            if rows:
                # Calculate gains for symbols pairs beginning with the second symbol in pair
                calculated_gains_list = []  # List to store gains for each symbol

                for row in rows:
                    symbol = row[0]
                    bid_price = float(row[1])
                    ask_price = float(row[2])
                    gains_info = calculate_gains_based_on_arbitrage(symbol, 100, ask_price, bid_price)

                    # Append gains_info to the list
                    calculated_gains_list.append(gains_info)

                if calculated_gains_list:  # Check if the list is not empty
                    # Find and return the symbol with the highest arbitrage gain
                    highest_gain_symbol = max(calculated_gains_list, key=lambda gains_info: gains_info['net_gain'])
                    symbol_pair = highest_gain_symbol['symbol']
                    new_second_symbol_in_pair = symbol_pair[3:]
                    return highest_gain_symbol, new_second_symbol_in_pair
                else:
                    print(f"No matching symbols found for {second_symbol_in_pair}. Trying variations.")

            # If no matches found, try removing the first character
            second_symbol_in_pair = second_symbol_in_pair[1:]

            if not second_symbol_in_pair:
                break  # Break the loop if the string becomes empty

        print("No matching symbol found for variations.")
        return None, None
    except Error as e:
        print(f"Error fetching data from the database: {e}")


if __name__ == "__main__":
    # Reopen the database connection
    db_connection = create_connection()

    # Initialize second_symbol_in_pair outside the loop
    second_symbol_in_pair = 'ETH'

    try:
        while True:
            highest_gain_symbol, second_symbol_in_pair = fetch_symbol_info(db_connection, second_symbol_in_pair)
            
            if highest_gain_symbol:
                print("\nPair with the highest arbitrage gain:")
                print(f"Symbol: {highest_gain_symbol['symbol']}, Net Gain: {highest_gain_symbol['net_gain']}")

                # Fetch new opportunities with the second symbol in the pair
                result = fetch_symbol_info_with_second_symbol_in_pair(db_connection, second_symbol_in_pair)

                if result:
                    highest_gain_symbol, new_second_symbol_in_pair = result
                    print('Highest gain symbol for the second symbol in the pair:', highest_gain_symbol)
                    print('Next second symbol in pair:', new_second_symbol_in_pair)
                    second_symbol_in_pair = new_second_symbol_in_pair
                else:
                    print("No more matching symbols found for variations. Exiting loop.")
                    break

            # Add a delay to avoid overwhelming the system
            time.sleep(0.5)  # Adjust the delay time as needed

    finally:
        # Close the database connection after the loop completes
        if db_connection:
            db_connection.close()
