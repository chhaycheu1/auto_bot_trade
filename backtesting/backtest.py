"""
Backtester Module

Runs trading strategy backtests on historical data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Use Agg backend for headless servers (must be before importing pyplot)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys
sys.path.append('..')
from core.strategy import TradingStrategy, SignalType
from config.settings import BACKTEST_SETTINGS, RISK_SETTINGS
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestTrade:
    """Represents a trade in backtest."""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    side: str
    pnl: float
    pnl_pct: float
    exit_reason: str
    signal_score: float


@dataclass
class BacktestResult:
    """Backtest results container."""
    symbol: str
    interval: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_trade_pnl: float
    avg_winner: float
    avg_loser: float
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: pd.Series = None
    
    def print_summary(self):
        """Print formatted backtest summary."""
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Symbol: {self.symbol} | Interval: {self.interval}")
        print(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        print("-" * 60)
        print(f"Initial Capital:  ${self.initial_capital:,.2f}")
        print(f"Final Capital:    ${self.final_capital:,.2f}")
        print(f"Total Return:     {self.total_return_pct:+.2f}%")
        print("-" * 60)
        print(f"Total Trades:     {self.total_trades}")
        print(f"Winning Trades:   {self.winning_trades}")
        print(f"Losing Trades:    {self.losing_trades}")
        print(f"Win Rate:         {self.win_rate:.1f}%")
        print("-" * 60)
        print(f"Profit Factor:    {self.profit_factor:.2f}")
        print(f"Max Drawdown:     {self.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio:     {self.sharpe_ratio:.2f}")
        print("-" * 60)
        print(f"Avg Trade P&L:    ${self.avg_trade_pnl:.2f}")
        print(f"Avg Winner:       ${self.avg_winner:.2f}")
        print(f"Avg Loser:        ${self.avg_loser:.2f}")
        print("=" * 60 + "\n")


class Backtester:
    """
    Backtesting engine for the trading strategy.
    
    Simulates trades on historical data and calculates performance metrics.
    """
    
    def __init__(
        self,
        initial_capital: float = None,
        commission: float = None,
        slippage: float = None,
        risk_settings: Dict = None,
        strategy = None
    ):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital in USDT
            commission: Trading commission (e.g., 0.001 for 0.1%)
            slippage: Estimated slippage (e.g., 0.0005 for 0.05%)
            risk_settings: Risk management settings
            strategy: Optional strategy instance (uses TradingStrategy if not provided)
        """
        self.initial_capital = initial_capital or BACKTEST_SETTINGS['default_initial_capital']
        self.commission = commission or BACKTEST_SETTINGS['default_commission']
        self.slippage = slippage or BACKTEST_SETTINGS['default_slippage']
        self.risk_settings = risk_settings or RISK_SETTINGS
        
        # Use provided strategy or default
        self.strategy = strategy if strategy else TradingStrategy()
    
    def run(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        show_trades: bool = False
    ) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair
            interval: Kline interval
            show_trades: Print each trade as it happens
            
        Returns:
            BacktestResult with performance metrics
        """
        logger.info(f"Starting backtest for {symbol} {interval}")
        logger.info(f"Data range: {df.index[0]} to {df.index[-1]} ({len(df)} candles)")
        
        # Initialize state
        capital = self.initial_capital
        position = None  # {'side': 'BUY', 'price': x, 'quantity': y, 'time': z}
        trades: List[BacktestTrade] = []
        equity_curve = [capital]
        
        # Calculate indicators
        df = self.strategy.indicators.calculate_all(df)
        
        # We need at least 200 candles for indicators to stabilize
        warmup_period = 200
        
        for i in range(warmup_period, len(df)):
            current_df = df.iloc[:i+1]
            current_bar = df.iloc[i]
            current_price = current_bar['close']
            current_time = current_bar.name if hasattr(current_bar, 'name') else df.index[i]
            
            # Check exit conditions if in position
            if position is not None:
                exit_triggered, exit_reason = self._check_exit_conditions(
                    position, current_price, current_bar
                )
                
                if exit_triggered:
                    # Close position
                    exit_price = current_price * (1 - self.slippage)  # slippage on exit
                    
                    if position['side'] == 'BUY':
                        pnl = (exit_price - position['price']) * position['quantity']
                        pnl -= position['value'] * self.commission  # exit commission
                    else:
                        pnl = (position['price'] - exit_price) * position['quantity']
                        pnl -= position['value'] * self.commission
                    
                    pnl_pct = pnl / position['value'] * 100
                    capital += position['value'] + pnl
                    
                    trade = BacktestTrade(
                        entry_time=position['time'],
                        exit_time=current_time,
                        entry_price=position['price'],
                        exit_price=exit_price,
                        quantity=position['quantity'],
                        side=position['side'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        exit_reason=exit_reason,
                        signal_score=position.get('score', 0)
                    )
                    trades.append(trade)
                    
                    if show_trades:
                        logger.info(
                            f"CLOSE {position['side']} | {exit_reason} | "
                            f"Entry: {position['price']:.2f} | Exit: {exit_price:.2f} | "
                            f"P&L: {pnl:.2f} ({pnl_pct:+.2f}%)"
                        )
                    
                    position = None
            
            # Check for new signals if not in position
            if position is None:
                signal, _ = self.strategy.analyze(current_df)
                
                if signal.signal_type == SignalType.BUY:
                    # Open long position
                    position_size = capital * (self.risk_settings['default_position_size_pct'] / 100)
                    entry_price = current_price * (1 + self.slippage)  # slippage on entry
                    quantity = position_size / entry_price
                    
                    # Deduct commission
                    commission_cost = position_size * self.commission
                    capital -= position_size + commission_cost
                    
                    # Calculate stops
                    stop_loss = entry_price * (1 - self.risk_settings['stop_loss_pct'] / 100)
                    take_profit = entry_price * (1 + self.risk_settings['take_profit_pct'] / 100)
                    
                    position = {
                        'side': 'BUY',
                        'price': entry_price,
                        'quantity': quantity,
                        'value': position_size,
                        'time': current_time,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'highest_price': entry_price,
                        'trailing_stop': 0,
                        'score': signal.score
                    }
                    
                    if show_trades:
                        logger.info(
                            f"OPEN BUY | Score: {signal.score:.1f}% | "
                            f"Price: {entry_price:.2f} | Qty: {quantity:.6f} | "
                            f"SL: {stop_loss:.2f} | TP: {take_profit:.2f}"
                        )
            
            # Update equity curve
            if position is not None:
                unrealized_pnl = (current_price - position['price']) * position['quantity']
                equity_curve.append(capital + position['value'] + unrealized_pnl)
            else:
                equity_curve.append(capital)
        
        # Close any remaining position at the end
        if position is not None:
            current_price = df.iloc[-1]['close']
            exit_price = current_price * (1 - self.slippage)
            pnl = (exit_price - position['price']) * position['quantity']
            pnl -= position['value'] * self.commission
            capital += position['value'] + pnl
        
        # Calculate results
        result = self._calculate_results(
            symbol=symbol,
            interval=interval,
            start_date=df.index[0],
            end_date=df.index[-1],
            trades=trades,
            final_capital=capital,
            equity_curve=pd.Series(equity_curve)
        )
        
        logger.info(f"Backtest complete: {len(trades)} trades, {result.win_rate:.1f}% win rate")
        
        return result
    
    def _check_exit_conditions(
        self,
        position: Dict,
        current_price: float,
        current_bar: pd.Series
    ) -> Tuple[bool, str]:
        """Check if any exit conditions are triggered."""
        
        if position['side'] == 'BUY':
            # Update highest price for trailing stop
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Check stop loss
            if current_price <= position['stop_loss']:
                return True, 'stop_loss'
            
            # Check take profit
            if current_price >= position['take_profit']:
                return True, 'take_profit'
            
            # Check trailing stop
            if self.risk_settings['trailing_stop_enabled']:
                profit_pct = (current_price - position['price']) / position['price'] * 100
                
                if profit_pct >= self.risk_settings['trailing_stop_activation_pct']:
                    trailing_stop = position['highest_price'] * \
                        (1 - self.risk_settings['trailing_stop_distance_pct'] / 100)
                    position['trailing_stop'] = max(position['trailing_stop'], trailing_stop)
                    
                    if current_price <= position['trailing_stop']:
                        return True, 'trailing_stop'
            
            # Check RSI overbought for exit
            if current_bar.get('rsi_overbought', False):
                return True, 'rsi_overbought'
            
            # Check MACD bearish crossover
            if current_bar.get('macd_bearish_crossover', False):
                return True, 'macd_bearish'
        
        return False, ''
    
    def _calculate_results(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: datetime,
        trades: List[BacktestTrade],
        final_capital: float,
        equity_curve: pd.Series
    ) -> BacktestResult:
        """Calculate backtest performance metrics."""
        
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        total_return_pct = (final_capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown
        peak = equity_curve.expanding(min_periods=1).max()
        drawdown = (equity_curve - peak) / peak * 100
        max_drawdown = abs(drawdown.min())
        
        # Sharpe ratio (annualized, assuming daily returns)
        returns = equity_curve.pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Average metrics
        avg_trade_pnl = sum(t.pnl for t in trades) / total_trades if total_trades > 0 else 0
        avg_winner = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loser = gross_loss / len(losing_trades) if losing_trades else 0
        
        return BacktestResult(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return_pct=total_return_pct,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown_pct=max_drawdown,
            sharpe_ratio=sharpe,
            avg_trade_pnl=avg_trade_pnl,
            avg_winner=avg_winner,
            avg_loser=avg_loser,
            trades=trades,
            equity_curve=equity_curve
        )
    
    def plot_results(self, result: BacktestResult, save_path: str = None):
        """Plot backtest results."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Equity curve
        ax1 = axes[0, 0]
        result.equity_curve.plot(ax=ax1, color='blue', linewidth=1)
        ax1.set_title('Equity Curve')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.axhline(y=result.initial_capital, color='gray', linestyle='--', alpha=0.5)
        ax1.fill_between(result.equity_curve.index, 
                        result.initial_capital, 
                        result.equity_curve, 
                        alpha=0.3,
                        color='green' if result.final_capital > result.initial_capital else 'red')
        
        # Drawdown
        ax2 = axes[0, 1]
        peak = result.equity_curve.expanding(min_periods=1).max()
        drawdown = (result.equity_curve - peak) / peak * 100
        drawdown.plot(ax=ax2, color='red', linewidth=1)
        ax2.fill_between(drawdown.index, 0, drawdown, alpha=0.3, color='red')
        ax2.set_title('Drawdown')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Drawdown (%)')
        
        # Trade P&L distribution
        ax3 = axes[1, 0]
        pnls = [t.pnl for t in result.trades]
        colors = ['green' if p > 0 else 'red' for p in pnls]
        ax3.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
        ax3.set_title('Trade P&L Distribution')
        ax3.set_xlabel('Trade #')
        ax3.set_ylabel('P&L ($)')
        ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        # Summary stats
        ax4 = axes[1, 1]
        ax4.axis('off')
        stats_text = f"""
        BACKTEST SUMMARY
        {'='*40}
        Symbol: {result.symbol}
        Interval: {result.interval}
        
        Initial Capital: ${result.initial_capital:,.2f}
        Final Capital: ${result.final_capital:,.2f}
        Total Return: {result.total_return_pct:+.2f}%
        
        Total Trades: {result.total_trades}
        Win Rate: {result.win_rate:.1f}%
        Profit Factor: {result.profit_factor:.2f}
        
        Max Drawdown: {result.max_drawdown_pct:.2f}%
        Sharpe Ratio: {result.sharpe_ratio:.2f}
        """
        ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, 
                fontfamily='monospace', fontsize=10, verticalalignment='top')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
            logger.info(f"Chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
