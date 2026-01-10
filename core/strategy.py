"""
Trading Strategy Module

Implements the multi-indicator confirmation strategy with weighted scoring.
Generates buy/sell signals based on:
- EMA crossovers and trend
- RSI levels
- MACD crossovers and momentum
- Bollinger Bands
- Volume confirmation
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

import sys
sys.path.append('..')
from config.settings import SIGNAL_WEIGHTS, MIN_SIGNAL_SCORE, INDICATOR_SETTINGS
from core.indicators import TechnicalIndicators
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalType(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """Represents a trading signal with score and details."""
    signal_type: SignalType
    score: float
    price: float
    timestamp: pd.Timestamp
    details: Dict
    
    def __str__(self):
        return f"{self.signal_type.value} Signal @ {self.price:.2f} (Score: {self.score:.1f}%)"


class TradingStrategy:
    """
    Multi-indicator confirmation trading strategy.
    
    Uses weighted scoring system to generate high-confidence trading signals.
    """
    
    def __init__(
        self,
        signal_weights: Dict = None,
        min_score: float = None,
        indicator_settings: Dict = None
    ):
        """
        Initialize trading strategy.
        
        Args:
            signal_weights: Dictionary of indicator weights (must sum to 100)
            min_score: Minimum score required to generate a trade signal
            indicator_settings: Settings for technical indicators
        """
        self.weights = signal_weights or SIGNAL_WEIGHTS
        self.min_score = min_score or MIN_SIGNAL_SCORE
        self.indicators = TechnicalIndicators(indicator_settings)
        
        # Validate weights
        total_weight = sum(self.weights.values())
        if abs(total_weight - 100) > 0.01:
            logger.warning(f"Signal weights sum to {total_weight}, adjusting to 100")
            factor = 100 / total_weight
            self.weights = {k: v * factor for k, v in self.weights.items()}
    
    def analyze(self, df: pd.DataFrame) -> Tuple[TradingSignal, pd.DataFrame]:
        """
        Analyze market data and generate trading signal.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (TradingSignal, DataFrame with indicators)
        """
        # Calculate all indicators
        df = self.indicators.calculate_all(df)
        
        # Get scores for buy and sell signals
        buy_score, buy_details = self._calculate_buy_score(df)
        sell_score, sell_details = self._calculate_sell_score(df)
        
        latest = df.iloc[-1]
        timestamp = latest.name if hasattr(latest, 'name') else pd.Timestamp.now()
        price = float(latest['close'])
        
        # Determine signal type
        if buy_score >= self.min_score:
            signal = TradingSignal(
                signal_type=SignalType.BUY,
                score=buy_score,
                price=price,
                timestamp=timestamp,
                details=buy_details
            )
            logger.info(f"BUY signal generated: score={buy_score:.1f}%, price={price:.2f}")
            
        elif sell_score >= self.min_score:
            signal = TradingSignal(
                signal_type=SignalType.SELL,
                score=sell_score,
                price=price,
                timestamp=timestamp,
                details=sell_details
            )
            logger.info(f"SELL signal generated: score={sell_score:.1f}%, price={price:.2f}")
            
        else:
            signal = TradingSignal(
                signal_type=SignalType.HOLD,
                score=max(buy_score, sell_score),
                price=price,
                timestamp=timestamp,
                details={'buy_score': buy_score, 'sell_score': sell_score}
            )
        
        return signal, df
    
    def _calculate_buy_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        Calculate buy signal score based on indicator conditions.
        
        Returns:
            Tuple of (score, details dictionary)
        """
        latest = df.iloc[-1]
        score = 0.0
        details = {}
        
        # TREND FILTER: Don't buy in bearish trend (price below EMA 200)
        # This significantly improves win rate
        if 'ema_trend' in latest and latest['close'] < latest.get('ema_trend', latest['close']):
            return 0.0, {'trend_filter': 'blocked - price below EMA 200'}
        
        # 1. EMA Crossover Score
        ema_score = 0
        if latest['ema_short_above_medium']:
            ema_score += 50  # Short above medium
        if latest['price_above_ema_long']:
            ema_score += 30  # Price above long EMA (trend confirmation)
        if latest['ema_bullish_crossover']:
            ema_score += 20  # Recent crossover bonus
            
        ema_contribution = (ema_score / 100) * self.weights['ema_crossover']
        score += ema_contribution
        details['ema'] = {
            'raw_score': ema_score,
            'contribution': ema_contribution,
            'short_above_medium': bool(latest['ema_short_above_medium']),
            'price_above_long': bool(latest['price_above_ema_long']),
            'recent_crossover': bool(latest['ema_bullish_crossover'])
        }
        
        # 2. RSI Score (25%)
        rsi_score = 0
        rsi_value = latest['rsi']
        
        if 30 <= rsi_value <= 50:
            rsi_score = 100  # Ideal buy zone (recovering from oversold)
        elif 50 < rsi_value <= 60:
            rsi_score = 70  # Still acceptable
        elif 20 <= rsi_value < 30:
            rsi_score = 80  # Oversold, might bounce
        elif rsi_value < 20:
            rsi_score = 60  # Extremely oversold, risky
        else:
            rsi_score = 0  # Overbought, don't buy
            
        rsi_contribution = (rsi_score / 100) * self.weights['rsi']
        score += rsi_contribution
        details['rsi'] = {
            'value': float(rsi_value),
            'raw_score': rsi_score,
            'contribution': rsi_contribution,
            'in_buy_zone': bool(latest['rsi_buy_zone'])
        }
        
        # 3. MACD Score (25%)
        macd_score = 0
        if latest['macd_above_signal']:
            macd_score += 50
        if latest['macd_bullish_crossover']:
            macd_score += 30  # Recent crossover
        if latest['macd_histogram_positive']:
            macd_score += 20
            
        macd_contribution = (macd_score / 100) * self.weights['macd']
        score += macd_contribution
        details['macd'] = {
            'value': float(latest['macd']),
            'signal': float(latest['macd_signal']),
            'histogram': float(latest['macd_histogram']),
            'raw_score': macd_score,
            'contribution': macd_contribution,
            'bullish': bool(latest['macd_above_signal'])
        }
        
        # 4. Bollinger Bands Score (15%)
        bb_score = 0
        if latest['price_near_lower_bb']:
            bb_score = 100  # Near lower band = potential buy
        elif latest['price_below_middle_bb']:
            bb_score = 50  # Below middle is okay
        else:
            bb_score = 20  # Above middle, less attractive for buying
            
        bb_contribution = (bb_score / 100) * self.weights['bollinger_bands']
        score += bb_contribution
        details['bollinger_bands'] = {
            'lower': float(latest['bb_lower']),
            'middle': float(latest['bb_middle']),
            'upper': float(latest['bb_upper']),
            'raw_score': bb_score,
            'contribution': bb_contribution,
            'near_lower': bool(latest['price_near_lower_bb'])
        }
        
        # 5. Volume Score (10%)
        volume_score = 0
        if latest['volume_above_avg']:
            volume_ratio = latest['volume_ratio']
            if volume_ratio >= 2.0:
                volume_score = 100  # Very high volume
            elif volume_ratio >= 1.5:
                volume_score = 80
            else:
                volume_score = 60
        else:
            volume_score = 30  # Low volume is a weak signal
            
        volume_contribution = (volume_score / 100) * self.weights['volume']
        score += volume_contribution
        details['volume'] = {
            'current': float(latest['volume']),
            'average': float(latest['volume_sma']),
            'ratio': float(latest['volume_ratio']),
            'raw_score': volume_score,
            'contribution': volume_contribution,
            'above_avg': bool(latest['volume_above_avg'])
        }
        
        return score, details
    
    def _calculate_sell_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        Calculate sell signal score based on indicator conditions.
        
        Returns:
            Tuple of (score, details dictionary)
        """
        latest = df.iloc[-1]
        score = 0.0
        details = {}
        
        # 1. EMA Crossover Score (25%)
        ema_score = 0
        if not latest['ema_short_above_medium']:
            ema_score += 50  # Short below medium
        if not latest['price_above_ema_long']:
            ema_score += 30  # Price below long EMA
        if latest['ema_bearish_crossover']:
            ema_score += 20  # Recent bearish crossover
            
        ema_contribution = (ema_score / 100) * self.weights['ema_crossover']
        score += ema_contribution
        details['ema'] = {
            'raw_score': ema_score,
            'contribution': ema_contribution,
            'bearish_crossover': bool(latest['ema_bearish_crossover'])
        }
        
        # 2. RSI Score (25%)
        rsi_score = 0
        rsi_value = latest['rsi']
        
        if rsi_value >= 70:
            rsi_score = 100  # Overbought = sell
        elif rsi_value >= 60:
            rsi_score = 70  # Getting overbought
        else:
            rsi_score = 0  # Not overbought
            
        rsi_contribution = (rsi_score / 100) * self.weights['rsi']
        score += rsi_contribution
        details['rsi'] = {
            'value': float(rsi_value),
            'raw_score': rsi_score,
            'contribution': rsi_contribution,
            'overbought': bool(latest['rsi_overbought'])
        }
        
        # 3. MACD Score (25%)
        macd_score = 0
        if not latest['macd_above_signal']:
            macd_score += 50
        if latest['macd_bearish_crossover']:
            macd_score += 30
        if not latest['macd_histogram_positive']:
            macd_score += 20
            
        macd_contribution = (macd_score / 100) * self.weights['macd']
        score += macd_contribution
        details['macd'] = {
            'value': float(latest['macd']),
            'raw_score': macd_score,
            'contribution': macd_contribution,
            'bearish': not bool(latest['macd_above_signal'])
        }
        
        # 4. Bollinger Bands Score (15%)
        bb_score = 0
        if latest['price_near_upper_bb']:
            bb_score = 100  # Near upper band = potential sell
        elif not latest['price_below_middle_bb']:
            bb_score = 50  # Above middle
        else:
            bb_score = 20
            
        bb_contribution = (bb_score / 100) * self.weights['bollinger_bands']
        score += bb_contribution
        details['bollinger_bands'] = {
            'raw_score': bb_score,
            'contribution': bb_contribution,
            'near_upper': bool(latest['price_near_upper_bb'])
        }
        
        # 5. Volume Score (10%)
        volume_score = 0
        if latest['volume_above_avg']:
            volume_score = 80  # High volume confirms the move
        else:
            volume_score = 40
            
        volume_contribution = (volume_score / 100) * self.weights['volume']
        score += volume_contribution
        details['volume'] = {
            'ratio': float(latest['volume_ratio']),
            'raw_score': volume_score,
            'contribution': volume_contribution
        }
        
        return score, details
    
    def get_signal_summary(self, signal: TradingSignal) -> str:
        """Get a formatted summary of the trading signal."""
        lines = [
            f"{'='*50}",
            f"TRADING SIGNAL: {signal.signal_type.value}",
            f"{'='*50}",
            f"Price: {signal.price:.2f}",
            f"Overall Score: {signal.score:.1f}%",
            f"Threshold: {self.min_score}%",
            f"Timestamp: {signal.timestamp}",
            "",
            "Indicator Breakdown:",
            "-" * 30
        ]
        
        for indicator, data in signal.details.items():
            if isinstance(data, dict) and 'contribution' in data:
                lines.append(
                    f"  {indicator.upper()}: {data.get('contribution', 0):.1f}% "
                    f"(raw: {data.get('raw_score', 0):.0f})"
                )
        
        lines.append("=" * 50)
        return "\n".join(lines)
