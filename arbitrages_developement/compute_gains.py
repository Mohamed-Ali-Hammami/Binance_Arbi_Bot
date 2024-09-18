from decimal import Decimal
import pandas as pd


def compute_gain(ask, symbol, bid, fee_percentage, ask_volume, bid_volume, taker_fee, amount_in_dollars=100, slippage=0.001, network_fee=0.001, order_book_depth=100):
    try:
        # Convert all numeric values to Decimal
        adjusted_ask = Decimal(str(ask)) * (Decimal('1') + Decimal(str(slippage)))
        adjusted_bid = Decimal(str(bid)) * (Decimal('1') - Decimal(str(slippage)))

        if adjusted_ask <= Decimal('0') or adjusted_bid <= Decimal('0'):
            raise ValueError(f"Invalid adjusted_ask or adjusted_bid for symbol {symbol}")

        # Calculate the equivalent amount in crypto units based on the investment amount in dollars
        amount_in_crypto = Decimal(str(amount_in_dollars)) / Decimal(str(ask))

        # Calculate actual fees based on the trading volume
        fee = max(Decimal(str(ask)) * Decimal(str(ask_volume)) * Decimal(str(taker_fee)),
                  Decimal(str(bid)) * Decimal(str(bid_volume)) * Decimal(str(taker_fee)))

        # Calculate the actual buy and sell prices considering network fees
        actual_buy_price = adjusted_ask + Decimal(str(network_fee))
        actual_sell_price = adjusted_bid - Decimal(str(network_fee))

        # Calculate net gain in dollars for the provided investment amount
        net_gain_in_dollars = (actual_sell_price - actual_buy_price) * amount_in_crypto - fee

        # Return the calculated values
        return net_gain_in_dollars, amount_in_dollars + net_gain_in_dollars, fee, actual_sell_price, amount_in_crypto

    except (ValueError, TypeError) as e:
        # Handle specific errors
        print(f"Error calculating gain for symbol {symbol}: {e}")
        return None
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error calculating gain for symbol {symbol}: {e}")
        return None

    
def calculate_gains(row, amount):
    exchange = row['exchange']
    symbol = row['symbol']
    ask = Decimal(str(row['ask']))  # Convert to Decimal
    bid = Decimal(str(row['bid']))  # Convert to Decimal
    ask_volume = Decimal(str(row['ask_volume']))  # Convert to Decimal
    bid_volume = Decimal(str(row['bid_volume']))  # Convert to Decimal
    fee = Decimal(str(row['taker_fee']))  # Convert to Decimal

    if ask <= bid:
        return pd.Series({
            'exchange': exchange,
            'symbol': symbol,
            'ask': ask,
            'bid': bid,
            'gain': None,
            'gain_in_amount': None,
            'buy_fee': None,
            'sell_fee': None,
            'remaining_amount': amount,
        })

    # Use compute_gain to calculate gain-related values
    gain_in_dollars, new_amount, fee, actual_sell_price, amount_in_crypto = compute_gain(
        ask, symbol, bid, fee, ask_volume, bid_volume, amount
    )

    if gain_in_dollars > 0:
        # Calculate new remaining amount after successful trade
        remaining_amount = amount + gain_in_dollars

        return pd.Series({
            'exchange': exchange,
            'symbol': symbol,
            'ask': ask,
            'bid': bid,
            'gain': gain_in_dollars,
            'gain_in_amount': amount_in_crypto,
            'buy_fee': fee,
            'sell_fee': fee,
            'remaining_amount': remaining_amount,
        })
    else:
        # No gain, return remaining amount
        return pd.Series({
            'exchange': exchange,
            'symbol': symbol,
            'ask': ask,
            'bid': bid,
            'gain': None,
            'gain_in_amount': None,
            'buy_fee': None,
            'sell_fee': None,
            'remaining_amount': amount,
        })



#