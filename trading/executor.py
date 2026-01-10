"""
Order Executor Module

Handles order execution with proper error handling and confirmation.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
import sys
sys.path.append('..')
from core.binance_client import BinanceClient
from core.risk_manager import RiskManager
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderExecutor:
    """
    Executes trading orders on Binance.
    
    Handles:
    - Market order execution
    - Stop-loss and take-profit order placement
    - Order confirmation and tracking
    """
    
    def __init__(self, client: BinanceClient, risk_manager: RiskManager):
        """
        Initialize order executor.
        
        Args:
            client: Binance client instance
            risk_manager: Risk manager instance
        """
        self.client = client
        self.risk_manager = risk_manager
        self.pending_orders: Dict[str, Dict] = {}
    
    def execute_buy(
        self,
        symbol: str,
        current_price: float,
        signal_score: float = 0
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Execute a buy order with stop-loss and take-profit.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            signal_score: Signal strength for logging
            
        Returns:
            Tuple of (success, order_details)
        """
        # Check if trading is allowed
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            logger.warning(f"Trade blocked: {reason}")
            return False, {'error': reason}
        
        # Check if already have position
        if self.risk_manager.has_position(symbol):
            logger.warning(f"Already have position in {symbol}")
            return False, {'error': 'Position already exists'}
        
        try:
            # Calculate position size
            quantity = self.risk_manager.calculate_position_size(symbol, current_price)
            quantity = self.client.round_quantity(symbol, quantity)
            
            # Place market buy order
            order = self.client.place_market_order(
                symbol=symbol,
                side='BUY',
                quantity=quantity
            )
            
            # Get actual fill price
            fill_price = float(order.get('fills', [{}])[0].get('price', current_price))
            fill_qty = float(order.get('executedQty', quantity))
            
            # Open position in risk manager
            position = self.risk_manager.open_position(
                symbol=symbol,
                side='BUY',
                entry_price=fill_price,
                quantity=fill_qty
            )
            
            # Place stop-loss order
            try:
                sl_price = self.client.round_price(symbol, position.stop_loss)
                sl_order = self.client.place_stop_loss_order(
                    symbol=symbol,
                    side='SELL',
                    quantity=fill_qty,
                    stop_price=sl_price
                )
                self.pending_orders[f"{symbol}_SL"] = sl_order
            except Exception as e:
                logger.error(f"Failed to place stop-loss order: {e}")
            
            # Place take-profit order
            try:
                tp_price = self.client.round_price(symbol, position.take_profit)
                tp_order = self.client.place_take_profit_order(
                    symbol=symbol,
                    side='SELL',
                    quantity=fill_qty,
                    stop_price=tp_price
                )
                self.pending_orders[f"{symbol}_TP"] = tp_order
            except Exception as e:
                logger.error(f"Failed to place take-profit order: {e}")
            
            result = {
                'order_id': order['orderId'],
                'symbol': symbol,
                'side': 'BUY',
                'quantity': fill_qty,
                'price': fill_price,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'signal_score': signal_score,
                'timestamp': datetime.now()
            }
            
            logger.info(
                f"BUY executed: {fill_qty} {symbol} @ {fill_price:.2f} | "
                f"SL: {position.stop_loss:.2f} | TP: {position.take_profit:.2f}"
            )
            
            return True, result
            
        except Exception as e:
            logger.error(f"Failed to execute buy order: {e}")
            return False, {'error': str(e)}
    
    def execute_sell(
        self,
        symbol: str,
        current_price: float,
        reason: str = "signal"
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Execute a sell order to close position.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            reason: Reason for selling
            
        Returns:
            Tuple of (success, order_details)
        """
        position = self.risk_manager.get_position(symbol)
        if not position:
            logger.warning(f"No position to close for {symbol}")
            return False, {'error': 'No position to close'}
        
        try:
            # Cancel pending SL/TP orders
            self._cancel_pending_orders(symbol)
            
            # Place market sell order
            order = self.client.place_market_order(
                symbol=symbol,
                side='SELL',
                quantity=position.quantity
            )
            
            # Get actual fill price
            fill_price = float(order.get('fills', [{}])[0].get('price', current_price))
            
            # Close position in risk manager
            trade_result = self.risk_manager.close_position(
                symbol=symbol,
                exit_price=fill_price,
                reason=reason
            )
            
            result = {
                'order_id': order['orderId'],
                'symbol': symbol,
                'side': 'SELL',
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'exit_price': fill_price,
                'pnl': trade_result['pnl'],
                'pnl_pct': trade_result['pnl_pct'],
                'reason': reason,
                'timestamp': datetime.now()
            }
            
            logger.info(
                f"SELL executed: {position.quantity} {symbol} @ {fill_price:.2f} | "
                f"P&L: {trade_result['pnl']:.2f} ({trade_result['pnl_pct']:+.2f}%)"
            )
            
            return True, result
            
        except Exception as e:
            logger.error(f"Failed to execute sell order: {e}")
            return False, {'error': str(e)}
    
    def _cancel_pending_orders(self, symbol: str):
        """Cancel pending SL/TP orders for a symbol."""
        keys_to_remove = []
        
        for key, order in self.pending_orders.items():
            if symbol in key:
                try:
                    self.client.cancel_order(symbol, order['orderId'])
                    keys_to_remove.append(key)
                except Exception as e:
                    logger.error(f"Failed to cancel order {key}: {e}")
        
        for key in keys_to_remove:
            del self.pending_orders[key]
    
    def check_and_execute_exits(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Check exit conditions and execute if triggered.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            
        Returns:
            Trade result if exit executed, None otherwise
        """
        exit_reason = self.risk_manager.check_exit_conditions(symbol, current_price)
        
        if exit_reason:
            success, result = self.execute_sell(symbol, current_price, exit_reason)
            if success:
                return result
        
        return None
