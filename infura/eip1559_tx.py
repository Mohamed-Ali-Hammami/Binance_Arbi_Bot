import os
from dotenv import load_dotenv
import asyncio
import json
import websockets
import socketio
import logging
from web3.auto import w3 , Web3
from web3.middleware import geth_poa_middleware

# Add this middleware to handle PoA networks like Binance Smart Chain testnet
w3.middleware_onion.inject(geth_poa_middleware, layer=0)


load_dotenv()

infura_url = f'https://data-seed-prebsc-1-s1.binance.org:8545/'
provider = Web3(Web3.HTTPProvider(infura_url))
API_KEY = "BszIxANs/4dOdsFQO+ND7+b7K0sxmdoIIb1B9C54iMPxXQhdBMHFjA"
WEBSOCKET_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"
RECONNECT_INTERVAL = 0  # milliseconds
WEBSOCKET_TRADE_URL = "wss://testnet.binancefuture.com/ws/!miniTicker@arr"
logging.basicConfig(level=logging.INFO)


def analyze_arbitrage_opportunities(amount, bid_price, ask_price, slippage):
    buy_amount = amount / bid_price
    effective_ask_price = ask_price * (1 + slippage)
    sell_amount = buy_amount * effective_ask_price
    net_gain = float(sell_amount - amount)
    return {'net_gain': net_gain, 'is_profitable': net_gain > 0}
  
async def websocket_handler(socket_io):
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            logging.info("WebSocket connection established.")
            parameters = {}  # Dictionary to store dynamic parameters
            response = await websocket.recv()
            buffer = response

            # Check if the buffer starts with '[' and ends with ']'
            if buffer.startswith("[") and buffer.endswith("]"):
                try:
                    # Parse the entire array
                    symbol_infos = json.loads(buffer)
                    # Iterate over individual objects in the array
                    symbols_details = []
                    positive_opportunities = []
                    negative_opportunities = []

                    for symbol_info in symbol_infos:
                        parameters['amount'] = 100
                        parameters['slippage'] = 0.001
                        # Dynamic calculation of parameters based on data characteristics
                        bid_price = float(symbol_info.get('b'))
                        ask_price = float(symbol_info.get('a'))

                        volume = float(symbol_info.get('v'))
                        quote_volume = float(symbol_info.get('q'))

                        calculate_total_gains = analyze_arbitrage_opportunities(parameters['amount'], ask_price, bid_price, parameters['slippage'])
                        net_gain = calculate_total_gains.get('net_gain')
                        is_profitable = calculate_total_gains.get('is_profitable')
                        amount_in_bnb = '0.003'
                        gas_price_in_gwei = ''
                        token_in = ''
                        token_out =''
                        amount_out_min = ''
                        
                        if is_profitable:
                            # Execute the trade
                            execute_trade(contract_abi, from_account, amount_in_bnb, gas_price_in_gwei, token_in, token_out, amount_out_min)
                            print("Profit-taking completed.")
                        if net_gain > 0:
                            total_gains = net_gain
                            positive_opportunities.append({
                                        'total_gains': total_gains,
                                        'symbol': symbol_info.get('s', ''),
                                        'bid_price': symbol_info.get('b', 0),
                                        'ask_price': symbol_info.get('a', 0),
                                        'price_change': symbol_info.get('p', 0),
                                        'price_change_percent': symbol_info.get('P', 0),
                                        'weighted_avg_price': symbol_info.get('w', 0),
                                        'prev_day_close_price': symbol_info.get('x', 0),
                                        'current_day_close_price': symbol_info.get('c', 0),
                                        'close_trade_quantity': symbol_info.get('Q', 0),
                                        'bid_quantity': symbol_info.get('B', 0),
                                        'ask_quantity': symbol_info.get('A', 0),
                                        'open_price': symbol_info.get('o', 0),
                                        'high_price': symbol_info.get('h', 0),
                                        'low_price': symbol_info.get('l', 0),
                                        'bid_volume': symbol_info.get('v', 0),
                                        'ask_volume': symbol_info.get('q', 0),
                                        'open_time': symbol_info.get('O', 0),
                                        'close_time': symbol_info.get('C', 0),
                                        'first_trade_id': symbol_info.get('F', 0),
                                        'last_trade_id': symbol_info.get('L', 0),
                                        'total_trades': symbol_info.get('n', 0),

                                        })
                            symbols_details.append({
                                        'total_gains': total_gains,
                                        'symbol': symbol_info.get('s', ''),
                                        'bid_price': symbol_info.get('b', 0),
                                        'ask_price': symbol_info.get('a', 0),
                                        'price_change': symbol_info.get('p', 0),
                                        'price_change_percent': symbol_info.get('P', 0),
                                        'weighted_avg_price': symbol_info.get('w', 0),
                                        'prev_day_close_price': symbol_info.get('x', 0),
                                        'current_day_close_price': symbol_info.get('c', 0),
                                        'close_trade_quantity': symbol_info.get('Q', 0),
                                        'bid_quantity': symbol_info.get('B', 0),
                                        'ask_quantity': symbol_info.get('A', 0),
                                        'open_price': symbol_info.get('o', 0),
                                        'high_price': symbol_info.get('h', 0),
                                        'low_price': symbol_info.get('l', 0),
                                        'bid_volume': symbol_info.get('v', 0),
                                        'ask_volume': symbol_info.get('q', 0),
                                        'open_time': symbol_info.get('O', 0),
                                        'close_time': symbol_info.get('C', 0),
                                        'first_trade_id': symbol_info.get('F', 0),
                                        'last_trade_id': symbol_info.get('L', 0),
                                        'total_trades': symbol_info.get('n', 0),
                                     })
                        if net_gain < 0:
                            total_losses = net_gain
                            negative_opportunities.append({
                                        'total_losses': total_losses,
                                        'symbol': symbol_info.get('s', ''),
                                        'bid_price': symbol_info.get('b', 0),
                                        'ask_price': symbol_info.get('a', 0),
                                        'price_change': symbol_info.get('p', 0),
                                        'price_change_percent': symbol_info.get('P', 0),
                                        'weighted_avg_price': symbol_info.get('w', 0),
                                        'prev_day_close_price': symbol_info.get('x', 0),
                                        'current_day_close_price': symbol_info.get('c', 0),
                                        'close_trade_quantity': symbol_info.get('Q', 0),
                                        'bid_quantity': symbol_info.get('B', 0),
                                        'ask_quantity': symbol_info.get('A', 0),
                                        'open_price': symbol_info.get('o', 0),
                                        'high_price': symbol_info.get('h', 0),
                                        'low_price': symbol_info.get('l', 0),
                                        'bid_volume': symbol_info.get('v', 0),
                                        'ask_volume': symbol_info.get('q', 0),
                                        'open_time': symbol_info.get('O', 0),
                                        'close_time': symbol_info.get('C', 0),
                                        'first_trade_id': symbol_info.get('F', 0),
                                        'last_trade_id': symbol_info.get('L', 0),
                                        'total_trades': symbol_info.get('n', 0),
                                        })
                            symbols_details.append({
                                        'total_losses': total_losses,
                                        'symbol': symbol_info.get('s', ''),
                                        'bid_price': symbol_info.get('b', 0),
                                        'ask_price': symbol_info.get('a', 0),
                                        'price_change': symbol_info.get('p', 0),
                                        'price_change_percent': symbol_info.get('P', 0),
                                        'weighted_avg_price': symbol_info.get('w', 0),
                                        'prev_day_close_price': symbol_info.get('x', 0),
                                        'current_day_close_price': symbol_info.get('c', 0),
                                        'close_trade_quantity': symbol_info.get('Q', 0),
                                        'bid_quantity': symbol_info.get('B', 0),
                                        'ask_quantity': symbol_info.get('A', 0),
                                        'open_price': symbol_info.get('o', 0),
                                        'high_price': symbol_info.get('h', 0),
                                        'low_price': symbol_info.get('l', 0),
                                        'bid_volume': symbol_info.get('v', 0),
                                        'ask_volume': symbol_info.get('q', 0),
                                        'open_time': symbol_info.get('O', 0),
                                        'close_time': symbol_info.get('C', 0),
                                        'first_trade_id': symbol_info.get('F', 0),
                                        'last_trade_id': symbol_info.get('L', 0),
                                        'total_trades': symbol_info.get('n', 0),
                                     })


                except json.JSONDecodeError as json_error:
                            logging.error(f"Error decoding JSON array: {json_error}")


    except websockets.ConnectionClosedError as closed_error:
            logging.error(f"WebSocket connection closed unexpectedly: {closed_error}")


    except Exception as e:
        logging.error(f"Error in WebSocket connection: {e}")
                    # Sleep before attempting to reconnect
        await asyncio.sleep(RECONNECT_INTERVAL / 1000)  # Convert to seconds

    
def execute_trade(from_account, amount_in_bnb, gas_price_in_gwei,contract_abi, token_in, token_out, amount_out_min):
    nonce = provider.eth.get_transaction_count(from_account)
    tx = contract.functions.swapExactETHForTokens(amount_out_min, [token_in, token_out], from_account).buildTransaction({
        'nonce': nonce,
        'from': from_account,
        'value': provider.to_wei(amount_in_bnb, 'ether'),
        'gasPrice': provider.to_wei(gas_price_in_gwei, 'gwei'),
        'gas': 200000,
        'chainId': 97
    })
    private_key = os.getenv("PRIVATE_KEY")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    raw_transaction = signed_tx.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw_transaction)
    print("Transaction hash:", w3.to_hex(tx_hash))

    gas = w3.eth.estimate_gas(tx)
    print("Gas used:", gas)

    # Extracting the raw transaction from the signed transaction
    raw_transaction = signed_tx.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw_transaction)
    print("Transaction hash:", w3.to_hex(tx_hash))


def process_trade(contract_abi, symbol_info):
    print("Processing trade for symbol:", symbol_info['symbol'])
    # Implement logic for taking profit
    if symbol_info.get('total_gains', 0) > 0:
        print("Arbitrage opportunity detected! Taking profit...")
        # Define the parameters for executing the trade
        amount_in_bnb = symbol_info.get('amount_in_bnb', 0.05)
        gas_price_in_gwei = symbol_info.get('gas_price_in_gwei', 10.0)
        token_in = symbol_info.get('token_in')
        token_out = symbol_info.get('token_out')
        amount_out_min = symbol_info.get('amount_out_min')

        # Execute the trade
        execute_trade(contract_abi,from_account, amount_in_bnb, gas_price_in_gwei, token_in, token_out, amount_out_min)

        # Add any additional actions or logging specific to profit-taking
        print("Profit-taking completed.")
    else:
        print("No arbitrage opportunity detected for profit.\n")

if __name__ == "__main__":
    private_key = os.getenv("PRIVATE_KEY")
    from_account = os.getenv("PUBLIC_KEY")
# Replace with your contract address
    contract_abi = os.getenv("ABI")  # Replace with your contract ABI
    balance = w3.eth.get_balance(from_account)
    print("Before conversion:", from_account)
    print("Balance in wei:", balance)

    try:
        from_account = w3.to_checksum_address(from_account)
        print("After conversion:", from_account)
    except Exception as e:
        print(f"Invalid 'from_account' address: {from_account}")

    # You need to define socketio somewhere before passing it to the function
    socketio = None

    # Call your functions in the main block
    asyncio.run(websocket_handler(socketio))