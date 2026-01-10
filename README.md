# High-Winrate Binance Auto Trading Bot

A sophisticated Python-based auto trading bot for Binance that combines multiple technical indicators with signal confirmation to achieve high win rates (targeting 65-75%).

## Features

- 📊 **Multi-Indicator Strategy**: EMA + RSI + MACD + Bollinger Bands + Volume
- 🎯 **High Win Rate**: Only trades when all indicators align (targeting 65-75%)
- 🛡️ **Risk Management**: Stop-loss, take-profit, trailing stops, position sizing
- 📈 **Backtesting**: Test strategies on historical data before going live
- 💹 **Supported Pairs**: BTC/USDT, SOL/USDT
- ⏱️ **Timeframes**: 5m (scalping), 15m, 1h, 4h (swing trading)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp config/credentials.py.example config/credentials.py
# Edit credentials.py with your Binance API keys
```

### 3. Run Backtest First

```bash
python backtest_runner.py --symbol BTCUSDT --timeframe 1h --days 90
```

### 4. Paper Trading (Testnet)

```bash
python main.py --testnet --symbol BTCUSDT --timeframe 15m
```

### 5. Live Trading

```bash
python main.py --symbol BTCUSDT --timeframe 15m
```

## Strategy Overview

The bot uses a weighted scoring system requiring multiple indicator confirmation:

| Indicator | Weight | Buy Signal |
|-----------|--------|------------|
| EMA Crossover (9/21/50) | 25% | Short EMA crosses above medium EMA, price above long EMA |
| RSI (14) | 25% | Between 30-60 (recovering from oversold) |
| MACD | 25% | MACD line crosses above signal line |
| Bollinger Bands | 15% | Price near lower band |
| Volume | 10% | Above 20-period average |

A trade is executed when the combined signal score reaches 70% or higher.

## Risk Management

- **Position Size**: 1-2% of portfolio per trade
- **Stop Loss**: 1.5% from entry
- **Take Profit**: 3% from entry (1:2 risk-reward)
- **Trailing Stop**: Activates after 1.5% profit
- **Max Daily Loss**: 5% of portfolio

## Project Structure

```
auto-trading/
├── config/          # Configuration files
├── core/            # Core trading engine
├── trading/         # Signal and execution modules
├── backtesting/     # Backtesting engine
├── utils/           # Utilities
├── tests/           # Unit tests
├── main.py          # Live trading entry point
└── backtest_runner.py # Backtesting entry point
```

## Disclaimer

⚠️ **Trading cryptocurrencies carries significant risk.** This bot is for educational purposes. Always:
- Start with paper trading on Testnet
- Use only funds you can afford to lose
- Monitor positions regularly
- Set appropriate risk limits

## License

MIT License
