"""
Tests for Technical Indicators
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '..')

from core.indicators import TechnicalIndicators


def generate_sample_data(periods: int = 250) -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    
    # Generate realistic price data
    returns = np.random.normal(0.0002, 0.02, periods)
    close_prices = 40000 * np.cumprod(1 + returns)
    
    data = []
    for i, close in enumerate(close_prices):
        volatility = abs(returns[i]) * 2
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


class TestTechnicalIndicators:
    """Test suite for TechnicalIndicators class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.indicators = TechnicalIndicators()
        self.df = generate_sample_data(250)
    
    def test_calculate_ema(self):
        """Test EMA calculation."""
        df = self.indicators.calculate_ema(self.df.copy())
        
        # Check EMA columns exist
        assert 'ema_short' in df.columns
        assert 'ema_medium' in df.columns
        assert 'ema_long' in df.columns
        assert 'ema_trend' in df.columns
        
        # Check no NaN in later rows (after warmup)
        assert not df['ema_short'].iloc[-1:].isna().any()
        assert not df['ema_medium'].iloc[-1:].isna().any()
        
        # Check crossover signals
        assert 'ema_bullish_crossover' in df.columns
        assert 'ema_bearish_crossover' in df.columns
    
    def test_calculate_rsi(self):
        """Test RSI calculation."""
        df = self.indicators.calculate_rsi(self.df.copy())
        
        # Check RSI column exists
        assert 'rsi' in df.columns
        
        # Check RSI is bounded between 0 and 100
        rsi_values = df['rsi'].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()
        
        # Check zone indicators
        assert 'rsi_oversold' in df.columns
        assert 'rsi_overbought' in df.columns
        assert 'rsi_buy_zone' in df.columns
    
    def test_calculate_macd(self):
        """Test MACD calculation."""
        df = self.indicators.calculate_macd(self.df.copy())
        
        # Check MACD columns exist
        assert 'macd' in df.columns
        assert 'macd_signal' in df.columns
        assert 'macd_histogram' in df.columns
        
        # Check crossover signals
        assert 'macd_bullish_crossover' in df.columns
        assert 'macd_bearish_crossover' in df.columns
        
        # Histogram should be MACD - Signal
        latest = df.iloc[-1]
        expected_hist = latest['macd'] - latest['macd_signal']
        assert abs(latest['macd_histogram'] - expected_hist) < 0.01
    
    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        df = self.indicators.calculate_bollinger_bands(self.df.copy())
        
        # Check BB columns exist
        assert 'bb_lower' in df.columns
        assert 'bb_middle' in df.columns
        assert 'bb_upper' in df.columns
        
        # Upper should be above middle, middle above lower
        latest = df.iloc[-1]
        assert latest['bb_upper'] > latest['bb_middle']
        assert latest['bb_middle'] > latest['bb_lower']
        
        # Middle should be close to SMA
        sma = df['close'].rolling(20).mean().iloc[-1]
        assert abs(latest['bb_middle'] - sma) < 1
    
    def test_calculate_volume_sma(self):
        """Test Volume SMA calculation."""
        df = self.indicators.calculate_volume_sma(self.df.copy())
        
        # Check columns exist
        assert 'volume_sma' in df.columns
        assert 'volume_above_avg' in df.columns
        assert 'volume_ratio' in df.columns
        
        # Volume ratio should be positive
        assert (df['volume_ratio'].dropna() > 0).all()
    
    def test_calculate_all(self):
        """Test calculating all indicators at once."""
        df = self.indicators.calculate_all(self.df.copy())
        
        # Check all major indicators exist
        assert 'ema_short' in df.columns
        assert 'rsi' in df.columns
        assert 'macd' in df.columns
        assert 'bb_middle' in df.columns
        assert 'volume_sma' in df.columns
    
    def test_get_current_signals(self):
        """Test getting current signal values."""
        df = self.indicators.calculate_all(self.df.copy())
        signals = self.indicators.get_current_signals(df)
        
        # Check signal dictionary has expected keys
        assert 'price' in signals
        assert 'rsi' in signals
        assert 'ema_bullish' in signals
        assert 'macd_bullish' in signals
        assert 'volume_above_avg' in signals


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
