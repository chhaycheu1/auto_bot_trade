"""
Position Manager Module

Tracks and manages trading positions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import csv
import os


@dataclass  
class TradeRecord:
    """Record of a completed trade."""
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: datetime
    reason: str
    signal_score: float = 0.0
    

class PositionManager:
    """
    Manages position tracking and trade history.
    """
    
    def __init__(self, trade_log_file: str = "trades.csv"):
        """
        Initialize position manager.
        
        Args:
            trade_log_file: Path to trade log CSV file
        """
        self.trade_log_file = trade_log_file
        self.trades: List[TradeRecord] = []
        self.trade_counter = 0
        
        # Load existing trades
        self._load_trades()
    
    def _load_trades(self):
        """Load trades from CSV file."""
        if os.path.exists(self.trade_log_file):
            try:
                with open(self.trade_log_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.trades.append(TradeRecord(
                            id=row['id'],
                            symbol=row['symbol'],
                            side=row['side'],
                            entry_price=float(row['entry_price']),
                            exit_price=float(row['exit_price']),
                            quantity=float(row['quantity']),
                            pnl=float(row['pnl']),
                            pnl_pct=float(row['pnl_pct']),
                            entry_time=datetime.fromisoformat(row['entry_time']),
                            exit_time=datetime.fromisoformat(row['exit_time']),
                            reason=row['reason'],
                            signal_score=float(row.get('signal_score', 0))
                        ))
                        self.trade_counter = max(
                            self.trade_counter, 
                            int(row['id'].split('-')[1])
                        )
            except Exception as e:
                print(f"Error loading trades: {e}")
    
    def record_trade(self, trade_data: Dict) -> TradeRecord:
        """
        Record a completed trade.
        
        Args:
            trade_data: Dictionary with trade details
            
        Returns:
            TradeRecord object
        """
        self.trade_counter += 1
        
        record = TradeRecord(
            id=f"TRADE-{self.trade_counter:05d}",
            symbol=trade_data['symbol'],
            side=trade_data['side'],
            entry_price=trade_data['entry_price'],
            exit_price=trade_data['exit_price'],
            quantity=trade_data['quantity'],
            pnl=trade_data['pnl'],
            pnl_pct=trade_data['pnl_pct'],
            entry_time=trade_data.get('entry_time', datetime.now()),
            exit_time=trade_data.get('exit_time', datetime.now()),
            reason=trade_data.get('reason', 'unknown'),
            signal_score=trade_data.get('signal_score', 0)
        )
        
        self.trades.append(record)
        self._save_trade(record)
        
        return record
    
    def _save_trade(self, record: TradeRecord):
        """Save a trade to CSV file."""
        file_exists = os.path.exists(self.trade_log_file)
        
        with open(self.trade_log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'id', 'symbol', 'side', 'entry_price', 'exit_price',
                'quantity', 'pnl', 'pnl_pct', 'entry_time', 'exit_time',
                'reason', 'signal_score'
            ])
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'id': record.id,
                'symbol': record.symbol,
                'side': record.side,
                'entry_price': record.entry_price,
                'exit_price': record.exit_price,
                'quantity': record.quantity,
                'pnl': record.pnl,
                'pnl_pct': record.pnl_pct,
                'entry_time': record.entry_time.isoformat(),
                'exit_time': record.exit_time.isoformat(),
                'reason': record.reason,
                'signal_score': record.signal_score
            })
    
    def get_trades(
        self,
        symbol: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = None
    ) -> List[TradeRecord]:
        """
        Get filtered trade history.
        
        Args:
            symbol: Filter by symbol
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of trades to return
            
        Returns:
            List of TradeRecord objects
        """
        trades = self.trades
        
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        
        if start_date:
            trades = [t for t in trades if t.exit_time >= start_date]
        
        if end_date:
            trades = [t for t in trades if t.exit_time <= end_date]
        
        if limit:
            trades = trades[-limit:]
        
        return trades
    
    def get_statistics(self, symbol: str = None) -> Dict:
        """
        Get trading statistics.
        
        Args:
            symbol: Filter by symbol
            
        Returns:
            Dictionary with statistics
        """
        trades = self.get_trades(symbol=symbol)
        
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in trades)
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / total_trades * 100 if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / total_trades if total_trades > 0 else 0,
            'avg_win': total_wins / len(winning_trades) if winning_trades else 0,
            'avg_loss': total_losses / len(losing_trades) if losing_trades else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
            'best_trade': max(t.pnl for t in trades),
            'worst_trade': min(t.pnl for t in trades),
            'avg_signal_score': sum(t.signal_score for t in trades) / total_trades if total_trades > 0 else 0
        }
    
    def print_summary(self, symbol: str = None):
        """Print a formatted summary of trading statistics."""
        stats = self.get_statistics(symbol)
        
        print("\n" + "=" * 50)
        print("TRADING SUMMARY")
        if symbol:
            print(f"Symbol: {symbol}")
        print("=" * 50)
        print(f"Total Trades:    {stats['total_trades']}")
        print(f"Winning Trades:  {stats['winning_trades']}")
        print(f"Losing Trades:   {stats['losing_trades']}")
        print(f"Win Rate:        {stats['win_rate']:.1f}%")
        print("-" * 50)
        print(f"Total P&L:       ${stats['total_pnl']:.2f}")
        print(f"Average P&L:     ${stats['avg_pnl']:.2f}")
        print(f"Average Win:     ${stats['avg_win']:.2f}")
        print(f"Average Loss:    ${stats['avg_loss']:.2f}")
        print(f"Profit Factor:   {stats['profit_factor']:.2f}")
        print("-" * 50)
        print(f"Best Trade:      ${stats['best_trade']:.2f}")
        print(f"Worst Trade:     ${stats['worst_trade']:.2f}")
        print("=" * 50 + "\n")
