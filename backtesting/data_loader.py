"""
Data Loader Module

Handles loading and caching historical market data.
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional
import sys
sys.path.append('..')
from utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """
    Load and cache historical market data for backtesting.
    """
    
    def __init__(self, cache_dir: str = "data_cache"):
        """
        Initialize data loader.
        
        Args:
            cache_dir: Directory to cache historical data
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def load_data(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: datetime = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Load historical data, using cache if available.
        
        Args:
            symbol: Trading pair
            interval: Kline interval
            start_date: Start date
            end_date: End date (defaults to now)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with OHLCV data
        """
        if end_date is None:
            end_date = datetime.now()
        
        cache_file = self._get_cache_path(symbol, interval, start_date, end_date)
        
        if use_cache and os.path.exists(cache_file):
            logger.info(f"Loading cached data from {cache_file}")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        
        # If no cache, we need to fetch from Binance
        logger.info(f"No cached data found for {symbol} {interval}")
        return pd.DataFrame()
    
    def save_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ):
        """Save data to cache."""
        cache_file = self._get_cache_path(symbol, interval, start_date, end_date)
        df.to_csv(cache_file)
        logger.info(f"Cached data saved to {cache_file}")
    
    def _get_cache_path(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Generate cache file path."""
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        return os.path.join(
            self.cache_dir,
            f"{symbol}_{interval}_{start_str}_{end_str}.csv"
        )
    
    def load_from_binance(
        self,
        client,
        symbol: str,
        interval: str,
        days: int = 90
    ) -> pd.DataFrame:
        """
        Load data directly from Binance API.
        
        Args:
            client: BinanceClient instance
            symbol: Trading pair
            interval: Kline interval
            days: Number of days of historical data
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching {days} days of data for {symbol} {interval} from Binance")
        
        df = client.get_historical_klines(symbol, interval, days)
        
        if not df.empty:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            self.save_data(df, symbol, interval, start_date, end_date)
        
        return df
    
    def generate_sample_data(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        days: int = 90,
        start_price: float = 40000
    ) -> pd.DataFrame:
        """
        Generate sample OHLCV data for testing.
        
        Args:
            symbol: Trading pair (for reference)
            interval: Kline interval
            days: Number of days
            start_price: Starting price
            
        Returns:
            DataFrame with generated OHLCV data
        """
        import numpy as np
        
        # Calculate number of candles
        candles_per_day = {
            '1m': 1440, '5m': 288, '15m': 96, '1h': 24, '4h': 6, '1d': 1
        }
        num_candles = days * candles_per_day.get(interval, 24)
        
        # Generate random walk
        np.random.seed(42)  # For reproducibility
        returns = np.random.normal(0.0001, 0.02, num_candles)
        prices = start_price * np.cumprod(1 + returns)
        
        # Generate OHLCV
        data = []
        for i, close in enumerate(prices):
            volatility = abs(returns[i]) * 2
            high = close * (1 + volatility)
            low = close * (1 - volatility)
            open_price = prices[i-1] if i > 0 else start_price
            volume = np.random.uniform(100, 10000)
            
            data.append({
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame with datetime index
        freq_map = {'1m': 'T', '5m': '5T', '15m': '15T', '1h': 'H', '4h': '4H', '1d': 'D'}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        index = pd.date_range(start=start_date, periods=num_candles, freq=freq_map.get(interval, 'H'))
        df = pd.DataFrame(data, index=index)
        
        logger.info(f"Generated {num_candles} candles of sample data")
        return df
