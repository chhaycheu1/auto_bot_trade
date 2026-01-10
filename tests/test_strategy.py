"""
Tests for Trading Strategy
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
sys.path.insert(0, '..')

from core.strategy import TradingStrategy, SignalType, TradingSignal


def generate_bullish_data(periods: int = 250) -> pd.DataFrame:
    """Generate bullish sample data - uptrend."""
    np.random.seed(42)
    
    # Uptrend with positive drift
    returns = np.random.normal(0.002, 0.015, periods)  # Positive mean
    close_prices = 40000 * np.cumprod(1 + returns)
    
    data = []
    for i, close in enumerate(close_prices):
        volatility = abs(returns[i]) * 1.5
        high = close * (1 + volatility)
        low = close * (1 - volatility * 0.5)  # Smaller wicks down
        open_price = close_prices[i-1] if i > 0 else 40000
        volume = np.random.uniform(2000, 15000)  # Higher volume
        
        data.append({
            'open': open_price,
            'high': max(open_price, high, close),
            'low': min(open_price, low, close),
            'close': close,
            'volume': volume
        })
    
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
    return pd.DataFrame(data, index=dates)


def generate_bearish_data(periods: int = 250) -> pd.DataFrame:
    """Generate bearish sample data - downtrend."""
    np.random.seed(123)
    
    # Downtrend with negative drift
    returns = np.random.normal(-0.002, 0.015, periods)  # Negative mean
    close_prices = 40000 * np.cumprod(1 + returns)
    
    data = []
    for i, close in enumerate(close_prices):
        volatility = abs(returns[i]) * 1.5
        high = close * (1 + volatility * 0.5)  # Smaller wicks up
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


class TestTradingStrategy:
    """Test suite for TradingStrategy class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = TradingStrategy()
    
    def test_strategy_initialization(self):
        """Test strategy initializes correctly."""
        assert self.strategy.min_score == 70
        assert sum(self.strategy.weights.values()) == 100
        assert self.strategy.indicators is not None
    
    def test_custom_weights(self):
        """Test strategy with custom weights."""
        custom_weights = {
            'ema_crossover': 30,
            'rsi': 30,
            'macd': 20,
            'bollinger_bands': 10,
            'volume': 10
        }
        strategy = TradingStrategy(signal_weights=custom_weights)
        assert strategy.weights == custom_weights
    
    def test_analyze_returns_signal(self):
        """Test analyze returns a valid signal."""
        df = generate_bullish_data()
        signal, df_result = self.strategy.analyze(df)
        
        assert isinstance(signal, TradingSignal)
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0 <= signal.score <= 100
        assert signal.price > 0
        assert signal.details is not None
    
    def test_analyze_returns_indicators(self):
        """Test analyze adds indicators to DataFrame."""
        df = generate_bullish_data()
        signal, df_result = self.strategy.analyze(df)
        
        # Check indicators were added
        assert 'ema_short' in df_result.columns
        assert 'rsi' in df_result.columns
        assert 'macd' in df_result.columns
        assert 'bb_middle' in df_result.columns
    
    def test_signal_details_structure(self):
        """Test signal details have expected structure."""
        df = generate_bullish_data()
        signal, _ = self.strategy.analyze(df)
        
        if signal.signal_type != SignalType.HOLD:
            assert 'ema' in signal.details
            assert 'rsi' in signal.details
            assert 'macd' in signal.details
            assert 'bollinger_bands' in signal.details
            assert 'volume' in signal.details
    
    def test_buy_score_calculation(self):
        """Test buy score is calculated correctly."""
        df = generate_bullish_data()
        df = self.strategy.indicators.calculate_all(df)
        
        score, details = self.strategy._calculate_buy_score(df)
        
        assert 0 <= score <= 100
        assert isinstance(details, dict)
        
        # Check all indicator contributions
        total_contribution = sum(
            d.get('contribution', 0) 
            for d in details.values() 
            if isinstance(d, dict)
        )
        assert abs(total_contribution - score) < 0.01
    
    def test_sell_score_calculation(self):
        """Test sell score is calculated correctly."""
        df = generate_bearish_data()
        df = self.strategy.indicators.calculate_all(df)
        
        score, details = self.strategy._calculate_sell_score(df)
        
        assert 0 <= score <= 100
        assert isinstance(details, dict)
    
    def test_signal_threshold(self):
        """Test signals respect minimum score threshold."""
        df = generate_bullish_data()
        
        # With high threshold, should mostly get HOLD signals
        high_threshold_strategy = TradingStrategy(min_score=90)
        signal, _ = high_threshold_strategy.analyze(df)
        
        if signal.signal_type != SignalType.HOLD:
            assert signal.score >= 90
    
    def test_get_signal_summary(self):
        """Test signal summary formatting."""
        df = generate_bullish_data()
        signal, _ = self.strategy.analyze(df)
        
        summary = self.strategy.get_signal_summary(signal)
        
        assert isinstance(summary, str)
        assert signal.signal_type.value in summary
        assert str(int(signal.score)) in summary


class TestSignalType:
    """Test SignalType enum."""
    
    def test_signal_types(self):
        """Test all signal types exist."""
        assert SignalType.BUY.value == "BUY"
        assert SignalType.SELL.value == "SELL"
        assert SignalType.HOLD.value == "HOLD"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
