"""
Technical Indicators Module

Calculates all technical indicators used by the trading strategy:
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Volume SMA

Uses the 'ta' library which is compatible with Python 3.14+
"""

import pandas as pd
import numpy as np
from ta import trend, momentum, volatility, volume
from typing import Dict, Optional, Tuple
import sys
sys.path.append('..')
from config.settings import INDICATOR_SETTINGS


class TechnicalIndicators:
    """Calculate technical indicators for trading signals."""
    
    def __init__(self, settings: Dict = None):
        """
        Initialize with indicator settings.
        
        Args:
            settings: Dictionary of indicator parameters. Uses defaults if None.
        """
        self.settings = settings or INDICATOR_SETTINGS
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators and add them to the DataFrame.
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        # Ensure column names are lowercase
        df.columns = df.columns.str.lower()
        
        # Calculate all indicators
        df = self.calculate_ema(df)
        df = self.calculate_rsi(df)
        df = self.calculate_macd(df)
        df = self.calculate_bollinger_bands(df)
        df = self.calculate_volume_sma(df)
        
        return df
    
    def calculate_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMA indicators."""
        df['ema_short'] = trend.ema_indicator(df['close'], window=self.settings['ema_short'])
        df['ema_medium'] = trend.ema_indicator(df['close'], window=self.settings['ema_medium'])
        df['ema_long'] = trend.ema_indicator(df['close'], window=self.settings['ema_long'])
        df['ema_trend'] = trend.ema_indicator(df['close'], window=self.settings['ema_trend'])
        
        # EMA crossover signals
        df['ema_short_above_medium'] = df['ema_short'] > df['ema_medium']
        df['price_above_ema_long'] = df['close'] > df['ema_long']
        df['price_above_ema_trend'] = df['close'] > df['ema_trend']
        
        # Detect crossover (transition from below to above)
        df['ema_bullish_crossover'] = (
            df['ema_short_above_medium'] & 
            ~df['ema_short_above_medium'].shift(1).fillna(False)
        )
        df['ema_bearish_crossover'] = (
            ~df['ema_short_above_medium'] & 
            df['ema_short_above_medium'].shift(1).fillna(True)
        )
        
        return df
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI indicator."""
        df['rsi'] = momentum.rsi(df['close'], window=self.settings['rsi_period'])
        
        # RSI conditions
        df['rsi_oversold'] = df['rsi'] < self.settings['rsi_oversold']
        df['rsi_overbought'] = df['rsi'] > self.settings['rsi_overbought']
        df['rsi_buy_zone'] = (
            (df['rsi'] >= self.settings['rsi_buy_min']) & 
            (df['rsi'] <= self.settings['rsi_buy_max'])
        )
        
        # RSI recovering from oversold
        df['rsi_recovering'] = (
            (df['rsi'] > self.settings['rsi_oversold']) &
            (df['rsi'].shift(1) <= self.settings['rsi_oversold'])
        )
        
        return df
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicator."""
        macd_indicator = trend.MACD(
            df['close'],
            window_slow=self.settings['macd_slow'],
            window_fast=self.settings['macd_fast'],
            window_sign=self.settings['macd_signal']
        )
        
        df['macd'] = macd_indicator.macd()
        df['macd_signal'] = macd_indicator.macd_signal()
        df['macd_histogram'] = macd_indicator.macd_diff()
        
        # MACD crossover signals
        df['macd_above_signal'] = df['macd'] > df['macd_signal']
        df['macd_bullish_crossover'] = (
            df['macd_above_signal'] & 
            ~df['macd_above_signal'].shift(1).fillna(False)
        )
        df['macd_bearish_crossover'] = (
            ~df['macd_above_signal'] & 
            df['macd_above_signal'].shift(1).fillna(True)
        )
        
        # MACD momentum
        df['macd_positive'] = df['macd'] > 0
        df['macd_histogram_positive'] = df['macd_histogram'] > 0
        
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        bb_indicator = volatility.BollingerBands(
            df['close'],
            window=self.settings['bb_period'],
            window_dev=self.settings['bb_std']
        )
        
        df['bb_lower'] = bb_indicator.bollinger_lband()
        df['bb_middle'] = bb_indicator.bollinger_mavg()
        df['bb_upper'] = bb_indicator.bollinger_hband()
        df['bb_bandwidth'] = bb_indicator.bollinger_wband()
        df['bb_percent'] = bb_indicator.bollinger_pband()
        
        # Bollinger Band conditions
        df['price_near_lower_bb'] = df['close'] <= df['bb_lower'] * 1.02  # Within 2% of lower band
        df['price_near_upper_bb'] = df['close'] >= df['bb_upper'] * 0.98  # Within 2% of upper band
        df['price_below_middle_bb'] = df['close'] < df['bb_middle']
        
        return df
    
    def calculate_volume_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Volume SMA for volume confirmation."""
        df['volume_sma'] = df['volume'].rolling(window=self.settings['volume_sma_period']).mean()
        df['volume_above_avg'] = df['volume'] > (df['volume_sma'] * self.settings['volume_multiplier'])
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def get_current_signals(self, df: pd.DataFrame) -> Dict:
        """
        Get the current indicator values and signals from the latest row.
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary with current indicator values and signals
        """
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        return {
            'timestamp': latest.name if hasattr(latest, 'name') else None,
            'price': latest['close'],
            
            # EMA values
            'ema_short': latest['ema_short'],
            'ema_medium': latest['ema_medium'],
            'ema_long': latest['ema_long'],
            'ema_trend': latest.get('ema_trend'),
            'ema_bullish': latest['ema_short_above_medium'] and latest['price_above_ema_long'],
            
            # RSI
            'rsi': latest['rsi'],
            'rsi_buy_zone': latest['rsi_buy_zone'],
            'rsi_oversold': latest['rsi_oversold'],
            'rsi_overbought': latest['rsi_overbought'],
            
            # MACD
            'macd': latest['macd'],
            'macd_signal': latest['macd_signal'],
            'macd_histogram': latest['macd_histogram'],
            'macd_bullish': latest['macd_above_signal'],
            'macd_bullish_crossover': latest['macd_bullish_crossover'],
            
            # Bollinger Bands
            'bb_lower': latest['bb_lower'],
            'bb_middle': latest['bb_middle'],
            'bb_upper': latest['bb_upper'],
            'price_near_lower_bb': latest['price_near_lower_bb'],
            'price_near_upper_bb': latest['price_near_upper_bb'],
            
            # Volume
            'volume': latest['volume'],
            'volume_sma': latest['volume_sma'],
            'volume_above_avg': latest['volume_above_avg'],
            'volume_ratio': latest['volume_ratio']
        }
