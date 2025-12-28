import math
from datetime import datetime, timedelta

def get_atm_strike(spot_price, step=50):
    return round(spot_price / step) * step

def get_scrip_symbol(index_name, strike, option_type, expiry_str):
    return f"{index_name}{expiry_str}{strike}{option_type}"

def calculate_stop_loss(entry_price, transaction_type, sl_points):
    if transaction_type == "B":
        return entry_price - sl_points
    else:
        return entry_price + sl_points

def calculate_target(entry_price, transaction_type, target_points):
    if transaction_type == "B":
        return entry_price + target_points
    else:
        return entry_price - target_points

def get_current_weekly_expiry():
    """
    Returns the date string for the nearest upcoming Thursday (Weekly Expiry).
    Format: DDMMM (e.g., 24APR).
    Note: Kotak Neo format might vary (e.g. 24APR24).
    We will produce "DDMMM" format (e.g. 25APR) as commonly used,
    but user might need to adjust based on specific year requirement.
    """
    today = datetime.now()
    # Thursday is 3
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7

    # If today is Thursday (weekday=3), days_ahead is 0.
    # We should allow trading on expiry day, so we keep it as 0.
    # Only if it's past market hours (e.g. > 3:30 PM), we might want next week,
    # but that's a user decision. Default to today if Thursday.

    if today.weekday() == 3:
        days_ahead = 0

    expiry_date = today + timedelta(days=days_ahead)

    # Format: 24APR (UpperCase)
    # %d is day, %b is Month abbr
    formatted = expiry_date.strftime("%d%b").upper()

    # Correction: Often API expects Year too. e.g. "24APR24" or just "24APR".
    # We will stick to DDMMM for now as placeholder or maybe DDMMMYY.
    # Let's try to include Year to be safe: DDMMMYY -> 25APR24
    formatted_with_year = expiry_date.strftime("%d%b%y").upper()
    return formatted_with_year
