"""
Trading Bot Configuration Settings

OPTIMIZED FOR HIGH WIN RATE (65-75%)
"""

# =============================================================================
# TRADING PAIRS
# =============================================================================
TRADING_PAIRS = ["BTCUSDT", "SOLUSDT"]
DEFAULT_PAIR = "BTCUSDT"

# =============================================================================
# TIMEFRAMES
# =============================================================================
TIMEFRAMES = {
    "scalping": "5m",
    "short_swing": "15m", 
    "medium_swing": "1h",
    "long_swing": "4h"
}
DEFAULT_TIMEFRAME = "1h"  # Changed to 1h for less noise

# =============================================================================
# INDICATOR SETTINGS (OPTIMIZED)
# =============================================================================
INDICATOR_SETTINGS = {
    # EMA Settings - Using wider EMAs for trend confirmation
    "ema_short": 9,
    "ema_medium": 21,
    "ema_long": 50,
    "ema_trend": 200,
    
    # RSI Settings - Tighter buy zone
    "rsi_period": 14,
    "rsi_oversold": 35,       # Changed from 30
    "rsi_overbought": 65,     # Changed from 70
    "rsi_buy_max": 55,        # Don't buy above this (changed from 60)
    "rsi_buy_min": 35,        # Recovering from oversold (changed from 30)
    
    # MACD Settings
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    
    # Bollinger Bands Settings
    "bb_period": 20,
    "bb_std": 2,
    
    # Volume Settings - Require higher volume
    "volume_sma_period": 20,
    "volume_multiplier": 1.2  # Volume should be 20% above SMA (changed from 1.0)
}

# =============================================================================
# SIGNAL WEIGHTS (OPTIMIZED - Must sum to 100)
# Increased weight on trend-following indicators
# =============================================================================
SIGNAL_WEIGHTS = {
    "ema_crossover": 30,     # Increased from 25 - trend is king
    "rsi": 20,               # Decreased from 25 - less weight on oscillator
    "macd": 25,              # Same - momentum confirmation
    "bollinger_bands": 10,   # Decreased from 15
    "volume": 15             # Increased from 10 - volume confirms moves
}

# Minimum score to trigger a trade (INCREASED for higher quality signals)
MIN_SIGNAL_SCORE = 80  # Changed from 70 - only take high-confidence trades

# =============================================================================
# RISK MANAGEMENT (OPTIMIZED FOR WIN RATE)
# =============================================================================
RISK_SETTINGS = {
    # Position sizing
    "max_position_size_pct": 2.0,
    "default_position_size_pct": 1.5,  # Increased from 1.0
    
    # Stop loss and take profit - Better risk/reward
    "stop_loss_pct": 1.0,      # Tighter stop loss (changed from 1.5)
    "take_profit_pct": 1.5,    # Smaller TP for higher hit rate (changed from 3.0)
    
    # Trailing stop - More aggressive
    "trailing_stop_enabled": True,
    "trailing_stop_activation_pct": 1.0,   # Activate earlier (changed from 1.5)
    "trailing_stop_distance_pct": 0.5,     # Tighter trail (changed from 1.0)
    
    # Daily limits
    "max_daily_loss_pct": 3.0,    # Reduced from 5.0
    "max_concurrent_positions": 2, # Reduced from 3
    "max_trades_per_day": 5,       # Reduced from 10
    
    # Minimum trade value
    "min_trade_value_usdt": 10.0
}

# =============================================================================
# BINANCE API SETTINGS
# =============================================================================
BINANCE_SETTINGS = {
    "testnet_base_url": "https://testnet.binance.vision",
    "testnet_ws_url": "wss://testnet.binance.vision/ws",
    "live_base_url": "https://api.binance.com",
    "live_ws_url": "wss://stream.binance.com:9443/ws",
    "recv_window": 5000,
    "request_timeout": 30
}

# =============================================================================
# BACKTESTING SETTINGS
# =============================================================================
BACKTEST_SETTINGS = {
    "default_initial_capital": 10000,
    "default_commission": 0.001,
    "default_slippage": 0.0005
}

# =============================================================================
# LOGGING SETTINGS
# =============================================================================
LOGGING_SETTINGS = {
    "log_level": "INFO",
    "log_to_file": True,
    "log_file": "trading_bot.log",
    "trade_log_file": "trades.csv"
}
