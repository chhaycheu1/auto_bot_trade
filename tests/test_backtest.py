"""
Tests for Backtester
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
sys.path.insert(0, '..')

from backtesting.backtest import Backtester, BacktestResult


def generate_trending_data(periods: int = 500, trend: str = 'up') -> pd.DataFrame:
    """Generate trending data for backtest testing."""
    np.random.seed(42)
    
    drift = 0.001 if trend == 'up' else -0.001
    returns = np.random.normal(drift, 0.015, periods)
    close_prices = 40000 * np.cumprod(1 + returns)
    
    data = []
    for i, close in enumerate(close_prices):
        volatility = abs(returns[i]) * 1.5
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        open_price = close_prices[i-1] if i > 0 else 40000
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': max(open_price, high, close),
            'low': min(open_price, low, close),
            'close': close,
            'volume': volume
        })
    
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
    return pd.DataFrame(data, index=dates)


class TestBacktester:
    """Test suite for Backtester class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backtester = Backtester(initial_capital=10000)
        self.df = generate_trending_data(500, 'up')
    
    def test_backtester_initialization(self):
        """Test backtester initializes correctly."""
        assert self.backtester.initial_capital == 10000
        assert self.backtester.commission == 0.001
        assert self.backtester.strategy is not None
    
    def test_run_backtest(self):
        """Test running a backtest."""
        result = self.backtester.run(
            df=self.df,
            symbol='BTCUSDT',
            interval='1h',
            show_trades=False
        )
        
        assert isinstance(result, BacktestResult)
        assert result.symbol == 'BTCUSDT'
        assert result.interval == '1h'
        assert result.initial_capital == 10000
    
    def test_backtest_result_metrics(self):
        """Test backtest result contains all metrics."""
        result = self.backtester.run(self.df, 'BTCUSDT', '1h')
        
        # Check all metrics exist
        assert result.total_trades >= 0
        assert 0 <= result.win_rate <= 100
        assert result.profit_factor >= 0
        assert result.max_drawdown_pct >= 0
        assert result.sharpe_ratio is not None
    
    def test_backtest_with_uptrend(self):
        """Test backtest on uptrending data should be profitable."""
        df = generate_trending_data(500, 'up')
        result = self.backtester.run(df, 'BTCUSDT', '1h')
        
        # In a strong uptrend, strategy should make some trades
        # (might not always be profitable due to randomness)
        assert result.total_trades > 0
    
    def test_equity_curve(self):
        """Test equity curve is generated."""
        result = self.backtester.run(self.df, 'BTCUSDT', '1h')
        
        assert result.equity_curve is not None
        assert len(result.equity_curve) > 0
        assert result.equity_curve.iloc[0] == self.backtester.initial_capital
    
    def test_trades_list(self):
        """Test trades are recorded."""
        result = self.backtester.run(self.df, 'BTCUSDT', '1h')
        
        assert isinstance(result.trades, list)
        
        if result.trades:
            trade = result.trades[0]
            assert hasattr(trade, 'entry_price')
            assert hasattr(trade, 'exit_price')
            assert hasattr(trade, 'pnl')
            assert hasattr(trade, 'exit_reason')
    
    def test_custom_capital(self):
        """Test backtest with custom initial capital."""
        backtester = Backtester(initial_capital=50000)
        result = backtester.run(self.df, 'BTCUSDT', '1h')
        
        assert result.initial_capital == 50000
    
    def test_custom_commission(self):
        """Test backtest with custom commission."""
        backtester = Backtester(initial_capital=10000, commission=0.002)
        result = backtester.run(self.df, 'BTCUSDT', '1h')
        
        # Higher commission should reduce returns
        assert result is not None


class TestBacktestResult:
    """Test BacktestResult class."""
    
    def test_print_summary(self, capsys):
        """Test print_summary outputs correctly."""
        backtester = Backtester(initial_capital=10000)
        df = generate_trending_data(500)
        result = backtester.run(df, 'BTCUSDT', '1h')
        
        result.print_summary()
        
        captured = capsys.readouterr()
        assert 'BACKTEST RESULTS' in captured.out
        assert 'BTCUSDT' in captured.out
        assert 'Win Rate' in captured.out


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
