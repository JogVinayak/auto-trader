"""
Trading Fee Calculator - Zerodha Fee Structure
Based on: https://zerodha.com/brokerage-calculator
"""

from typing import Dict


def calculate_trading_fees(
    quantity: int,
    price: float,
    trade_type: str,  # "BUY" or "SELL"
    exchange: str = "NSE"  # "NSE" or "BSE"
) -> Dict[str, float]:
    """
    Calculate all trading fees based on Zerodha's fee structure.

    Returns:
        Dict with breakdown of all fees and total cost
    """

    turnover = quantity * price

    # 1. Brokerage: ₹20 or 0.03% whichever is lower (for intraday/F&O)
    # For delivery: 0% (Zerodha is free for delivery)
    # We'll use 0.03% for paper trading to simulate realistic costs
    brokerage = min(20.0, turnover * 0.0003)

    # 2. STT (Securities Transaction Tax): 0.1% on sell side only
    stt = 0.0
    if trade_type == "SELL":
        stt = turnover * 0.001  # 0.1%

    # 3. Exchange Transaction Charges
    # NSE: 0.00325% (₹3.25 per lakh)
    # BSE: 0.003% (₹3 per lakh)
    if exchange == "NSE":
        exchange_charges = turnover * 0.0000325
    else:  # BSE
        exchange_charges = turnover * 0.00003

    # 4. GST: 18% on (brokerage + exchange charges)
    gst = (brokerage + exchange_charges) * 0.18

    # 5. SEBI Charges: ₹10 per crore
    sebi_charges = (turnover / 10000000) * 10  # ₹10 per crore

    # 6. Stamp Duty: 0.015% on buy side, 0.003% on sell side
    if trade_type == "BUY":
        stamp_duty = turnover * 0.00015  # 0.015%
    else:  # SELL
        stamp_duty = turnover * 0.00003  # 0.003%

    # Total Charges
    total_charges = (
        brokerage +
        stt +
        exchange_charges +
        gst +
        sebi_charges +
        stamp_duty
    )

    # Net Amount
    if trade_type == "BUY":
        net_amount = turnover + total_charges
    else:  # SELL
        net_amount = turnover - total_charges

    return {
        "turnover": round(turnover, 2),
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange_charges": round(exchange_charges, 2),
        "gst": round(gst, 2),
        "sebi_charges": round(sebi_charges, 4),
        "stamp_duty": round(stamp_duty, 2),
        "total_charges": round(total_charges, 2),
        "net_amount": round(net_amount, 2),
        "breakeven_price": round(_calculate_breakeven(price, total_charges, quantity, trade_type), 2)
    }


def _calculate_breakeven(price: float, total_charges: float, quantity: int, trade_type: str) -> float:
    """Calculate breakeven price including all charges"""
    if trade_type == "BUY":
        # Need to sell at this price to recover buy price + charges
        return price + (total_charges / quantity)
    else:
        # Already sold, breakeven is sell price minus charges
        return price - (total_charges / quantity)


def calculate_max_quantity(
    available_funds: float,
    stock_price: float,
    fund_percentage: float = 100.0
) -> Dict[str, any]:
    """
    Calculate maximum quantity that can be bought with available funds.

    Args:
        available_funds: Total cash available
        stock_price: Current stock price
        fund_percentage: Percentage of funds to use (default 100%)

    Returns:
        Dict with max quantity and cost breakdown
    """

    # Calculate funds to use
    funds_to_use = available_funds * (fund_percentage / 100.0)

    # Estimate charges (approximate)
    # We need to solve: funds_to_use = (quantity * price) + charges
    # This is iterative because charges depend on quantity

    max_qty = 0
    for qty in range(1, 10000):  # Max limit to avoid infinite loop
        fees = calculate_trading_fees(qty, stock_price, "BUY")
        if fees["net_amount"] > funds_to_use:
            max_qty = qty - 1
            break
        max_qty = qty

    if max_qty <= 0:
        return {
            "max_quantity": 0,
            "total_cost": 0,
            "remaining_funds": available_funds,
            "message": "Insufficient funds to buy even 1 share"
        }

    final_fees = calculate_trading_fees(max_qty, stock_price, "BUY")

    return {
        "max_quantity": max_qty,
        "total_cost": final_fees["net_amount"],
        "remaining_funds": round(available_funds - final_fees["net_amount"], 2),
        "per_share_cost": round(final_fees["net_amount"] / max_qty, 2),
        "total_charges": final_fees["total_charges"],
        "message": f"You can buy {max_qty} shares at ₹{stock_price:.2f}"
    }


if __name__ == "__main__":
    # Example usage
    print("=== BUY Example ===")
    buy_fees = calculate_trading_fees(10, 250.0, "BUY")
    for key, value in buy_fees.items():
        print(f"{key}: ₹{value}")

    print("\n=== SELL Example ===")
    sell_fees = calculate_trading_fees(10, 260.0, "SELL")
    for key, value in sell_fees.items():
        print(f"{key}: ₹{value}")

    print("\n=== Max Quantity Example ===")
    max_qty = calculate_max_quantity(10000, 250.0, 50.0)
    for key, value in max_qty.items():
        print(f"{key}: {value}")
