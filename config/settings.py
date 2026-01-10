"""
Trading Bot Configuration Settings
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
DEFAULT_TIMEFRAME = "15m"

# =============================================================================
# INDICATOR SETTINGS
# =============================================================================
INDICATOR_SETTINGS = {
    # EMA Settings
    "ema_short": 9,
    "ema_medium": 21,
    "ema_long": 50,
    "ema_trend": 200,
    
    # RSI Settings
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "rsi_buy_max": 60,  # Don't buy above this
    "rsi_buy_min": 30,  # Recovering from oversold
    
    # MACD Settings
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    
    # Bollinger Bands Settings
    "bb_period": 20,
    "bb_std": 2,
    
    # Volume Settings
    "volume_sma_period": 20,
    "volume_multiplier": 1.0  # Volume should be above this * SMA
}

# =============================================================================
# SIGNAL WEIGHTS (Must sum to 100)
# =============================================================================
SIGNAL_WEIGHTS = {
    "ema_crossover": 25,
    "rsi": 25,
    "macd": 25,
    "bollinger_bands": 15,
    "volume": 10
}

# Minimum score to trigger a trade (0-100)
MIN_SIGNAL_SCORE = 70

# =============================================================================
# RISK MANAGEMENT
# =============================================================================
RISK_SETTINGS = {
    # Position sizing
    "max_position_size_pct": 2.0,  # Max 2% of portfolio per trade
    "default_position_size_pct": 1.0,  # Default 1%
    
    # Stop loss and take profit
    "stop_loss_pct": 1.5,  # 1.5% stop loss
    "take_profit_pct": 3.0,  # 3% take profit (1:2 risk-reward)
    
    # Trailing stop
    "trailing_stop_enabled": True,
    "trailing_stop_activation_pct": 1.5,  # Activate after 1.5% profit
    "trailing_stop_distance_pct": 1.0,  # Trail by 1%
    
    # Daily limits
    "max_daily_loss_pct": 5.0,  # Stop trading after 5% daily loss
    "max_concurrent_positions": 3,
    "max_trades_per_day": 10,
    
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
    "default_initial_capital": 10000,  # USDT
    "default_commission": 0.001,  # 0.1% commission (Binance standard)
    "default_slippage": 0.0005  # 0.05% slippage estimate
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
