"""
Helper Functions

Utility functions for the trading bot.
"""

from typing import Optional
from datetime import datetime, timedelta


def format_price(price: float, decimals: int = 2) -> str:
    """Format price with proper decimal places."""
    return f"${price:,.{decimals}f}"


def format_quantity(quantity: float, decimals: int = 6) -> str:
    """Format quantity with proper decimal places."""
    return f"{quantity:.{decimals}f}"


def format_pnl(pnl: float, pnl_pct: float = None) -> str:
    """Format P&L with color indicator."""
    sign = "+" if pnl >= 0 else ""
    result = f"{sign}${pnl:.2f}"
    if pnl_pct is not None:
        result += f" ({sign}{pnl_pct:.2f}%)"
    return result


def format_duration(start: datetime, end: datetime = None) -> str:
    """Format duration between two times."""
    if end is None:
        end = datetime.now()
    
    duration = end - start
    
    if duration.total_seconds() < 60:
        return f"{duration.total_seconds():.0f}s"
    elif duration.total_seconds() < 3600:
        return f"{duration.total_seconds() / 60:.0f}m"
    elif duration.total_seconds() < 86400:
        return f"{duration.total_seconds() / 3600:.1f}h"
    else:
        return f"{duration.days}d {(duration.total_seconds() % 86400) / 3600:.0f}h"


def interval_to_minutes(interval: str) -> int:
    """Convert interval string to minutes."""
    mapping = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
        '1d': 1440, '3d': 4320, '1w': 10080
    }
    return mapping.get(interval, 60)


def calculate_required_candles(interval: str, days: int) -> int:
    """Calculate number of candles needed for a given time period."""
    minutes = interval_to_minutes(interval)
    total_minutes = days * 24 * 60
    return total_minutes // minutes


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if divisor is zero."""
    if b == 0:
        return default
    return a / b


def calculate_pnl_pct(entry_price: float, exit_price: float, side: str) -> float:
    """Calculate P&L percentage based on entry/exit prices and side."""
    if side == 'BUY':
        return (exit_price - entry_price) / entry_price * 100
    else:
        return (entry_price - exit_price) / entry_price * 100


def get_symbol_base_quote(symbol: str) -> tuple:
    """
    Extract base and quote assets from symbol.
    Works for common patterns like BTCUSDT, ETHBTC, etc.
    """
    # Common quote assets
    quotes = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB']
    
    for quote in quotes:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            return base, quote
    
    return symbol, ''


def print_table(data: list, headers: list, title: str = None):
    """Print data as a formatted table."""
    if title:
        print(f"\n{title}")
        print("=" * 60)
    
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in data:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    
    # Print header
    header_row = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_row)
    print("-" * len(header_row))
    
    # Print data
    for row in data:
        print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)))
    
    print()
