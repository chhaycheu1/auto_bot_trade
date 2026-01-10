"""
Binance Auto Trading Bot - Main Entry Point

High-winrate trading bot using multi-indicator confirmation strategy.
Supports both live trading and testnet paper trading.

Usage:
    # Paper trading (testnet)
    python main.py --testnet --symbol BTCUSDT --timeframe 15m
    
    # Live trading
    python main.py --symbol BTCUSDT --timeframe 15m
"""

import argparse
import time
import signal
import sys
from datetime import datetime, date

from config.settings import (
    TRADING_PAIRS, DEFAULT_PAIR, DEFAULT_TIMEFRAME,
    RISK_SETTINGS, LOGGING_SETTINGS
)
from core.binance_client import BinanceClient
from core.strategy import TradingStrategy, SignalType
from core.risk_manager import RiskManager
from trading.signals import SignalGenerator
from trading.executor import OrderExecutor
from trading.position import PositionManager
from utils.logger import get_logger, log_signal, log_trade

# Try to import credentials
try:
    from config.credentials import (
        API_KEY, API_SECRET, TESTNET_API_KEY, TESTNET_API_SECRET
    )
except ImportError:
    API_KEY = API_SECRET = TESTNET_API_KEY = TESTNET_API_SECRET = None

logger = get_logger(__name__, LOGGING_SETTINGS['log_level'])


class TradingBot:
    """
    Main trading bot class.
    
    Orchestrates the trading loop:
    1. Fetch market data
    2. Calculate indicators
    3. Generate signals
    4. Execute trades
    5. Manage risk
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        testnet: bool = True,
        initial_balance: float = 10000
    ):
        """
        Initialize trading bot.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Candle timeframe (e.g., '15m', '1h')
            testnet: Use testnet for paper trading
            initial_balance: Starting balance for risk calculations
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.testnet = testnet
        self.running = False
        
        # Validate API credentials
        if testnet:
            if not TESTNET_API_KEY or not TESTNET_API_SECRET:
                raise ValueError(
                    "Testnet API keys not found. Please configure credentials.py"
                )
            api_key, api_secret = TESTNET_API_KEY, TESTNET_API_SECRET
        else:
            if not API_KEY or not API_SECRET:
                raise ValueError(
                    "Live API keys not found. Please configure credentials.py"
                )
            api_key, api_secret = API_KEY, API_SECRET
        
        # Initialize components
        logger.info(f"Initializing bot for {symbol} {timeframe} ({'TESTNET' if testnet else 'LIVE'})")
        
        self.client = BinanceClient(api_key, api_secret, testnet=testnet)
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager(initial_balance=initial_balance)
        self.signal_generator = SignalGenerator()
        self.executor = OrderExecutor(self.client, self.risk_manager)
        self.position_manager = PositionManager()
        
        # Get symbol info
        self.symbol_info = self.client.get_symbol_info(symbol)
        
        logger.info("Bot initialized successfully")
    
    def start(self):
        """Start the trading bot."""
        self.running = True
        logger.info(f"🚀 Starting trading bot for {self.symbol}")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Main trading loop
        self._trading_loop()
    
    def stop(self):
        """Stop the trading bot."""
        self.running = False
        logger.info("Stopping trading bot...")
        
        # Close WebSocket
        self.client.stop_websocket()
        
        # Print final stats
        self._print_stats()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.stop()
        sys.exit(0)
    
    def _trading_loop(self):
        """Main trading loop."""
        # Calculate loop interval based on timeframe
        interval_seconds = self._get_interval_seconds(self.timeframe)
        
        # Reset daily stats if new day
        last_date = date.today()
        
        while self.running:
            try:
                # Check for new day
                if date.today() != last_date:
                    self.risk_manager.reset_daily_stats()
                    last_date = date.today()
                
                # Fetch latest candles
                df = self.client.get_klines(
                    symbol=self.symbol,
                    interval=self.timeframe,
                    limit=300  # Enough for all indicators
                )
                
                if df.empty:
                    logger.warning("No data received, retrying...")
                    time.sleep(10)
                    continue
                
                current_price = float(df.iloc[-1]['close'])
                
                # Check exit conditions for existing position
                if self.risk_manager.has_position(self.symbol):
                    exit_result = self.executor.check_and_execute_exits(
                        self.symbol, current_price
                    )
                    if exit_result:
                        self.position_manager.record_trade(exit_result)
                        continue
                
                # Analyze market and generate signal
                trading_signal, df_with_indicators = self.strategy.analyze(df)
                
                # Log signal
                log_signal(
                    logger,
                    trading_signal.signal_type.value,
                    self.symbol,
                    trading_signal.score,
                    trading_signal.price
                )
                
                # Execute trade if signal is strong enough
                if trading_signal.signal_type == SignalType.BUY:
                    # Check if we can trade
                    can_trade, reason = self.risk_manager.can_trade()
                    
                    if can_trade:
                        # Create signal record
                        signal = self.signal_generator.create_signal(
                            symbol=self.symbol,
                            signal_type='BUY',
                            score=trading_signal.score,
                            price=current_price,
                            details=trading_signal.details
                        )
                        
                        # Execute buy
                        success, result = self.executor.execute_buy(
                            symbol=self.symbol,
                            current_price=current_price,
                            signal_score=trading_signal.score
                        )
                        
                        if success:
                            self.signal_generator.mark_executed(signal.id)
                            log_trade(
                                logger, 'BUY', self.symbol,
                                result['price'], result['quantity'],
                                score=f"{trading_signal.score:.1f}%"
                            )
                    else:
                        logger.info(f"Trade blocked: {reason}")
                
                elif trading_signal.signal_type == SignalType.SELL:
                    if self.risk_manager.has_position(self.symbol):
                        success, result = self.executor.execute_sell(
                            symbol=self.symbol,
                            current_price=current_price,
                            reason='signal'
                        )
                        
                        if success:
                            self.position_manager.record_trade(result)
                            log_trade(
                                logger, 'SELL', self.symbol,
                                result['exit_price'], result['quantity'],
                                pnl=f"${result['pnl']:.2f}"
                            )
                
                # Wait for next candle
                self._wait_for_next_candle(interval_seconds)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(30)
        
        self.stop()
    
    def _get_interval_seconds(self, timeframe: str) -> int:
        """Convert timeframe to seconds."""
        mapping = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900,
            '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400,
            '6h': 21600, '8h': 28800, '12h': 43200, '1d': 86400
        }
        return mapping.get(timeframe, 900)
    
    def _wait_for_next_candle(self, interval_seconds: int):
        """Wait until the next candle with some buffer."""
        # Calculate time until next candle
        now = datetime.now()
        seconds_into_interval = now.timestamp() % interval_seconds
        wait_time = interval_seconds - seconds_into_interval + 2  # 2 second buffer
        
        logger.debug(f"Waiting {wait_time:.0f}s for next candle")
        
        # Wait in small increments to allow for interrupts
        wait_end = time.time() + wait_time
        while time.time() < wait_end and self.running:
            time.sleep(min(10, wait_end - time.time()))
    
    def _print_stats(self):
        """Print trading statistics."""
        stats = self.risk_manager.get_stats()
        
        print("\n" + "=" * 50)
        print("TRADING SESSION SUMMARY")
        print("=" * 50)
        print(f"Symbol: {self.symbol} | Timeframe: {self.timeframe}")
        print(f"Mode: {'TESTNET' if self.testnet else 'LIVE'}")
        print("-" * 50)
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_pct']:+.2f}%)")
        print(f"Current Balance: ${stats['current_balance']:.2f}")
        print("=" * 50 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='High-Winrate Binance Auto Trading Bot'
    )
    parser.add_argument(
        '--symbol', '-s',
        type=str,
        default=DEFAULT_PAIR,
        choices=TRADING_PAIRS,
        help=f'Trading pair (default: {DEFAULT_PAIR})'
    )
    parser.add_argument(
        '--timeframe', '-t',
        type=str,
        default=DEFAULT_TIMEFRAME,
        choices=['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
        help=f'Timeframe (default: {DEFAULT_TIMEFRAME})'
    )
    parser.add_argument(
        '--testnet',
        action='store_true',
        help='Use Binance Testnet for paper trading'
    )
    parser.add_argument(
        '--balance',
        type=float,
        default=10000,
        help='Initial balance for risk calculations (default: 10000)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("🤖 HIGH-WINRATE BINANCE TRADING BOT")
    print("=" * 50)
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Mode: {'TESTNET (Paper Trading)' if args.testnet else 'LIVE TRADING'}")
    print(f"Initial Balance: ${args.balance:,.2f}")
    print("=" * 50 + "\n")
    
    if not args.testnet:
        print("⚠️  WARNING: You are about to start LIVE TRADING!")
        print("    Real money will be used. Please confirm.")
        confirm = input("Type 'YES' to continue: ")
        if confirm != 'YES':
            print("Aborted.")
            return
    
    # Start bot
    bot = TradingBot(
        symbol=args.symbol,
        timeframe=args.timeframe,
        testnet=args.testnet,
        initial_balance=args.balance
    )
    
    bot.start()


if __name__ == "__main__":
    main()
