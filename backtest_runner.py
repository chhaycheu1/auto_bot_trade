"""
Backtest Runner

Run backtests on historical data to validate strategy performance.

Usage:
    # Basic backtest with sample data
    python backtest_runner.py --symbol BTCUSDT --timeframe 1h --days 90
    
    # With live Binance data
    python backtest_runner.py --symbol BTCUSDT --timeframe 15m --days 60 --live-data
    
    # Save chart
    python backtest_runner.py --symbol BTCUSDT --timeframe 1h --days 90 --save-chart
"""

import argparse
from datetime import datetime, timedelta

from config.settings import TRADING_PAIRS, DEFAULT_PAIR, BACKTEST_SETTINGS
from backtesting.backtest import Backtester
from backtesting.data_loader import DataLoader
from utils.logger import get_logger

# Optional: Try to import Binance client for live data
try:
    from core.binance_client import BinanceClient
    from config.credentials import API_KEY, API_SECRET
    BINANCE_AVAILABLE = bool(API_KEY and API_SECRET)
except ImportError:
    BINANCE_AVAILABLE = False

logger = get_logger(__name__)


def run_backtest(
    symbol: str,
    timeframe: str,
    days: int,
    initial_capital: float,
    use_live_data: bool = False,
    show_trades: bool = False,
    save_chart: bool = False
):
    """
    Run a backtest with the specified parameters.
    
    Args:
        symbol: Trading pair
        timeframe: Candle timeframe
        days: Number of days of historical data
        initial_capital: Starting capital
        use_live_data: Fetch data from Binance API
        show_trades: Print each trade during backtest
        save_chart: Save performance chart to file
    """
    logger.info(f"Starting backtest for {symbol} {timeframe}")
    logger.info(f"Period: {days} days | Initial Capital: ${initial_capital:,.2f}")
    
    # Load data
    data_loader = DataLoader()
    
    if use_live_data and BINANCE_AVAILABLE:
        logger.info("Fetching live data from Binance...")
        client = BinanceClient(API_KEY, API_SECRET)
        df = data_loader.load_from_binance(client, symbol, timeframe, days)
    else:
        logger.info("Using generated sample data...")
        start_price = 42000 if 'BTC' in symbol else 100 if 'SOL' in symbol else 1000
        df = data_loader.generate_sample_data(
            symbol=symbol,
            interval=timeframe,
            days=days,
            start_price=start_price
        )
    
    if df.empty:
        logger.error("No data available for backtesting")
        return None
    
    logger.info(f"Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")
    
    # Run backtest
    backtester = Backtester(initial_capital=initial_capital)
    result = backtester.run(
        df=df,
        symbol=symbol,
        interval=timeframe,
        show_trades=show_trades
    )
    
    # Print results
    result.print_summary()
    
    # Save chart if requested
    if save_chart:
        chart_path = f"backtest_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        backtester.plot_results(result, save_path=chart_path)
    
    return result


def run_parameter_optimization(
    symbol: str,
    timeframe: str,
    days: int = 90
):
    """
    Run parameter optimization to find best settings.
    
    This tests different combinations of:
    - Signal threshold levels
    - Risk/reward ratios
    - Stop loss percentages
    """
    logger.info("Running parameter optimization...")
    
    # Load data once
    data_loader = DataLoader()
    start_price = 42000 if 'BTC' in symbol else 100
    df = data_loader.generate_sample_data(symbol, timeframe, days, start_price)
    
    # Parameter combinations to test
    thresholds = [60, 65, 70, 75, 80]
    stop_losses = [1.0, 1.5, 2.0, 2.5]
    take_profits = [2.0, 3.0, 4.0, 5.0]
    
    best_result = None
    best_params = None
    best_score = -float('inf')
    
    results = []
    
    for threshold in thresholds:
        for sl in stop_losses:
            for tp in take_profits:
                # Skip if risk/reward is too low
                if tp / sl < 1.5:
                    continue
                
                # Create custom settings
                from config.settings import RISK_SETTINGS
                custom_risk = RISK_SETTINGS.copy()
                custom_risk['stop_loss_pct'] = sl
                custom_risk['take_profit_pct'] = tp
                
                # Run backtest
                backtester = Backtester(risk_settings=custom_risk)
                backtester.strategy.min_score = threshold
                
                result = backtester.run(df, symbol, timeframe, show_trades=False)
                
                # Score = win rate * profit factor * (1 - max_dd/100)
                score = (
                    result.win_rate * 
                    min(result.profit_factor, 5) * 
                    (1 - result.max_drawdown_pct / 100)
                )
                
                results.append({
                    'threshold': threshold,
                    'stop_loss': sl,
                    'take_profit': tp,
                    'trades': result.total_trades,
                    'win_rate': result.win_rate,
                    'profit_factor': result.profit_factor,
                    'return_pct': result.total_return_pct,
                    'max_dd': result.max_drawdown_pct,
                    'score': score
                })
                
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_params = {
                        'threshold': threshold,
                        'stop_loss': sl,
                        'take_profit': tp
                    }
    
    # Print optimization results
    print("\n" + "=" * 80)
    print("OPTIMIZATION RESULTS")
    print("=" * 80)
    print(f"{'Threshold':>10} {'SL%':>6} {'TP%':>6} {'Trades':>7} {'Win%':>6} {'PF':>6} {'Return%':>9} {'MaxDD%':>7} {'Score':>8}")
    print("-" * 80)
    
    # Sort by score and show top 10
    results.sort(key=lambda x: x['score'], reverse=True)
    for r in results[:10]:
        print(
            f"{r['threshold']:>10} {r['stop_loss']:>6.1f} {r['take_profit']:>6.1f} "
            f"{r['trades']:>7} {r['win_rate']:>6.1f} {r['profit_factor']:>6.2f} "
            f"{r['return_pct']:>+9.2f} {r['max_dd']:>7.2f} {r['score']:>8.2f}"
        )
    
    print("-" * 80)
    print(f"\n🏆 BEST PARAMETERS:")
    print(f"   Signal Threshold: {best_params['threshold']}%")
    print(f"   Stop Loss: {best_params['stop_loss']}%")
    print(f"   Take Profit: {best_params['take_profit']}%")
    print(f"   Risk/Reward: 1:{best_params['take_profit']/best_params['stop_loss']:.1f}")
    print()
    
    return best_result, best_params


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Trading Strategy Backtester'
    )
    parser.add_argument(
        '--symbol', '-s',
        type=str,
        default=DEFAULT_PAIR,
        help=f'Trading pair (default: {DEFAULT_PAIR})'
    )
    parser.add_argument(
        '--timeframe', '-t',
        type=str,
        default='1h',
        choices=['5m', '15m', '30m', '1h', '4h', '1d'],
        help='Timeframe (default: 1h)'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=90,
        help='Days of historical data (default: 90)'
    )
    parser.add_argument(
        '--capital', '-c',
        type=float,
        default=BACKTEST_SETTINGS['default_initial_capital'],
        help=f"Initial capital (default: {BACKTEST_SETTINGS['default_initial_capital']})"
    )
    parser.add_argument(
        '--live-data',
        action='store_true',
        help='Fetch live data from Binance API'
    )
    parser.add_argument(
        '--show-trades',
        action='store_true',
        help='Print each trade during backtest'
    )
    parser.add_argument(
        '--save-chart',
        action='store_true',
        help='Save performance chart to file'
    )
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Run parameter optimization'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("📊 TRADING STRATEGY BACKTESTER")
    print("=" * 50)
    
    if args.optimize:
        run_parameter_optimization(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days
        )
    else:
        run_backtest(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            initial_capital=args.capital,
            use_live_data=args.live_data,
            show_trades=args.show_trades,
            save_chart=args.save_chart
        )


if __name__ == "__main__":
    main()
