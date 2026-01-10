"""
Signal Generator Module

Generates and manages trading signals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class SignalState(Enum):
    """Signal state."""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class Signal:
    """Trading signal with metadata."""
    id: str
    symbol: str
    signal_type: str  # 'BUY' or 'SELL'
    score: float
    price: float
    timestamp: datetime
    details: Dict = field(default_factory=dict)
    state: SignalState = SignalState.PENDING
    expiry_seconds: int = 60  # Signal expires after 60 seconds
    
    def is_expired(self) -> bool:
        """Check if signal has expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.expiry_seconds
    
    def is_valid(self) -> bool:
        """Check if signal is still valid for execution."""
        return self.state == SignalState.PENDING and not self.is_expired()


class SignalGenerator:
    """
    Generates and tracks trading signals.
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize signal generator.
        
        Args:
            max_history: Maximum number of signals to keep in history
        """
        self.max_history = max_history
        self.signals: List[Signal] = []
        self.signal_counter = 0
    
    def create_signal(
        self,
        symbol: str,
        signal_type: str,
        score: float,
        price: float,
        details: Dict = None
    ) -> Signal:
        """
        Create a new trading signal.
        
        Args:
            symbol: Trading pair
            signal_type: 'BUY' or 'SELL'
            score: Signal strength score (0-100)
            price: Price at signal generation
            details: Additional signal details
            
        Returns:
            Signal object
        """
        self.signal_counter += 1
        
        signal = Signal(
            id=f"SIG-{self.signal_counter:05d}",
            symbol=symbol,
            signal_type=signal_type,
            score=score,
            price=price,
            timestamp=datetime.now(),
            details=details or {}
        )
        
        self.signals.append(signal)
        
        # Trim history if needed
        if len(self.signals) > self.max_history:
            self.signals = self.signals[-self.max_history:]
        
        return signal
    
    def get_pending_signals(self, symbol: str = None) -> List[Signal]:
        """Get all pending (non-expired) signals."""
        signals = [s for s in self.signals if s.is_valid()]
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        return signals
    
    def get_latest_signal(self, symbol: str = None) -> Optional[Signal]:
        """Get the most recent valid signal."""
        signals = self.get_pending_signals(symbol)
        return signals[-1] if signals else None
    
    def mark_executed(self, signal_id: str):
        """Mark a signal as executed."""
        for signal in self.signals:
            if signal.id == signal_id:
                signal.state = SignalState.EXECUTED
                break
    
    def mark_cancelled(self, signal_id: str):
        """Mark a signal as cancelled."""
        for signal in self.signals:
            if signal.id == signal_id:
                signal.state = SignalState.CANCELLED
                break
    
    def get_signal_history(self, symbol: str = None, limit: int = 10) -> List[Signal]:
        """Get signal history."""
        signals = self.signals
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        return signals[-limit:]
    
    def get_stats(self, symbol: str = None) -> Dict:
        """Get signal statistics."""
        signals = self.signals
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        
        total = len(signals)
        executed = sum(1 for s in signals if s.state == SignalState.EXECUTED)
        cancelled = sum(1 for s in signals if s.state == SignalState.CANCELLED)
        expired = sum(1 for s in signals if s.state == SignalState.EXPIRED or s.is_expired())
        
        buy_signals = sum(1 for s in signals if s.signal_type == 'BUY')
        sell_signals = sum(1 for s in signals if s.signal_type == 'SELL')
        
        avg_score = sum(s.score for s in signals) / total if total > 0 else 0
        
        return {
            'total_signals': total,
            'executed': executed,
            'cancelled': cancelled,
            'expired': expired,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_score': avg_score
        }
