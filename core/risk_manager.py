"""
Risk Manager Module

Handles all risk management aspects:
- Position sizing
- Stop-loss and take-profit calculations
- Trailing stops
- Daily loss limits
- Max concurrent positions
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, date
import sys
sys.path.append('..')
from config.settings import RISK_SETTINGS
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float = 0.0
    take_profit: float = 0.0
    trailing_stop: float = 0.0
    trailing_stop_activated: bool = False
    highest_price: float = 0.0  # For trailing stop
    lowest_price: float = float('inf')  # For short positions
    
    @property
    def value(self) -> float:
        return self.entry_price * self.quantity
    
    def update_trailing_stop(self, current_price: float, settings: Dict) -> float:
        """Update trailing stop based on current price."""
        if self.side == 'BUY':
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            # Check if trailing stop should be activated
            profit_pct = (current_price - self.entry_price) / self.entry_price * 100
            
            if profit_pct >= settings['trailing_stop_activation_pct']:
                self.trailing_stop_activated = True
                new_trailing_stop = self.highest_price * (1 - settings['trailing_stop_distance_pct'] / 100)
                
                if new_trailing_stop > self.trailing_stop:
                    self.trailing_stop = new_trailing_stop
                    logger.info(f"Trailing stop updated to {self.trailing_stop:.2f}")
        
        return self.trailing_stop


@dataclass
class DailyStats:
    """Daily trading statistics for risk management."""
    date: date = field(default_factory=date.today)
    trades_count: int = 0
    total_pnl: float = 0.0
    winning_trades: int = 0
    losing_trades: int = 0
    
    @property
    def win_rate(self) -> float:
        if self.trades_count == 0:
            return 0.0
        return self.winning_trades / self.trades_count * 100


class RiskManager:
    """
    Risk management system for the trading bot.
    
    Manages:
    - Position sizing based on portfolio percentage
    - Stop-loss and take-profit levels
    - Trailing stops
    - Daily loss limits
    - Maximum concurrent positions
    """
    
    def __init__(self, settings: Dict = None, initial_balance: float = 10000):
        """
        Initialize risk manager.
        
        Args:
            settings: Risk settings dictionary
            initial_balance: Starting portfolio balance in USDT
        """
        self.settings = settings or RISK_SETTINGS
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        self.positions: Dict[str, Position] = {}
        self.daily_stats = DailyStats()
        self.trade_history: List[Dict] = []
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on risk rules.
        
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_stats.total_pnl / self.initial_balance * 100)
        if self.daily_stats.total_pnl < 0 and daily_loss_pct >= self.settings['max_daily_loss_pct']:
            return False, f"Daily loss limit reached ({daily_loss_pct:.1f}%)"
        
        # Check max trades per day
        if self.daily_stats.trades_count >= self.settings['max_trades_per_day']:
            return False, f"Max daily trades reached ({self.daily_stats.trades_count})"
        
        # Check max concurrent positions
        if len(self.positions) >= self.settings['max_concurrent_positions']:
            return False, f"Max concurrent positions reached ({len(self.positions)})"
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        symbol: str,
        current_price: float,
        use_default: bool = True
    ) -> float:
        """
        Calculate position size based on risk settings.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            use_default: Use default position size instead of max
            
        Returns:
            Position size in quote currency (USDT)
        """
        if use_default:
            pct = self.settings['default_position_size_pct']
        else:
            pct = self.settings['max_position_size_pct']
        
        position_value = self.current_balance * (pct / 100)
        
        # Ensure minimum trade value
        if position_value < self.settings['min_trade_value_usdt']:
            logger.warning(
                f"Position value {position_value:.2f} below minimum "
                f"{self.settings['min_trade_value_usdt']}"
            )
            position_value = self.settings['min_trade_value_usdt']
        
        # Calculate quantity
        quantity = position_value / current_price
        
        return quantity
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop-loss price.
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            
        Returns:
            Stop-loss price
        """
        sl_pct = self.settings['stop_loss_pct'] / 100
        
        if side == 'BUY':
            return entry_price * (1 - sl_pct)
        else:
            return entry_price * (1 + sl_pct)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take-profit price.
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            
        Returns:
            Take-profit price
        """
        tp_pct = self.settings['take_profit_pct'] / 100
        
        if side == 'BUY':
            return entry_price * (1 + tp_pct)
        else:
            return entry_price * (1 - tp_pct)
    
    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float
    ) -> Position:
        """
        Open a new position.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            entry_price: Entry price
            quantity: Position quantity
            
        Returns:
            Position object
        """
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=self.calculate_stop_loss(entry_price, side),
            take_profit=self.calculate_take_profit(entry_price, side),
            highest_price=entry_price,
            lowest_price=entry_price
        )
        
        self.positions[symbol] = position
        
        logger.info(
            f"Position opened: {side} {quantity:.6f} {symbol} @ {entry_price:.2f} | "
            f"SL: {position.stop_loss:.2f} | TP: {position.take_profit:.2f}"
        )
        
        return position
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "manual"
    ) -> Optional[Dict]:
        """
        Close an open position.
        
        Args:
            symbol: Trading pair
            exit_price: Exit price
            reason: Reason for closing (e.g., 'stop_loss', 'take_profit', 'signal')
            
        Returns:
            Trade result dictionary or None if no position
        """
        if symbol not in self.positions:
            logger.warning(f"No open position for {symbol}")
            return None
        
        position = self.positions.pop(symbol)
        
        # Calculate P&L
        if position.side == 'BUY':
            pnl = (exit_price - position.entry_price) * position.quantity
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100
        
        # Update stats
        self.daily_stats.trades_count += 1
        self.daily_stats.total_pnl += pnl
        
        if pnl > 0:
            self.daily_stats.winning_trades += 1
        else:
            self.daily_stats.losing_trades += 1
        
        self.current_balance += pnl
        
        result = {
            'symbol': symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'reason': reason
        }
        
        self.trade_history.append(result)
        
        logger.info(
            f"Position closed: {position.side} {symbol} | "
            f"Entry: {position.entry_price:.2f} | Exit: {exit_price:.2f} | "
            f"P&L: {pnl:.2f} ({pnl_pct:+.2f}%) | Reason: {reason}"
        )
        
        return result
    
    def check_exit_conditions(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[str]:
        """
        Check if any exit conditions are met for a position.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            
        Returns:
            Exit reason if should exit, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        if position.side == 'BUY':
            # Update trailing stop
            if self.settings['trailing_stop_enabled']:
                position.update_trailing_stop(current_price, self.settings)
            
            # Check stop loss
            if current_price <= position.stop_loss:
                return 'stop_loss'
            
            # Check trailing stop
            if position.trailing_stop_activated and current_price <= position.trailing_stop:
                return 'trailing_stop'
            
            # Check take profit
            if current_price >= position.take_profit:
                return 'take_profit'
        
        else:  # SELL position
            if current_price >= position.stop_loss:
                return 'stop_loss'
            if current_price <= position.take_profit:
                return 'take_profit'
        
        return None
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if there's an open position for a symbol."""
        return symbol in self.positions
    
    def get_stats(self) -> Dict:
        """Get current trading statistics."""
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history if t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_pnl': total_pnl,
            'total_pnl_pct': (self.current_balance - self.initial_balance) / self.initial_balance * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'open_positions': len(self.positions),
            'daily_trades': self.daily_stats.trades_count,
            'daily_pnl': self.daily_stats.total_pnl
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at start of each trading day)."""
        self.daily_stats = DailyStats()
        logger.info("Daily stats reset")


# Import missing type hint
from typing import Tuple
