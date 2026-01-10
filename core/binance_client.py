"""
Binance Client Module

Handles all interactions with the Binance API:
- Fetching market data (klines, ticker)
- Placing orders
- Managing account information
- WebSocket streaming for real-time data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import time
import json
import threading

from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
import websocket

import sys
sys.path.append('..')
from config.settings import BINANCE_SETTINGS
from utils.logger import get_logger

logger = get_logger(__name__)


class BinanceClient:
    """Wrapper for Binance API interactions."""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Binance client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: If True, use testnet endpoints
        """
        self.testnet = testnet
        
        if testnet:
            self.client = Client(
                api_key, 
                api_secret,
                testnet=True
            )
            self.ws_url = BINANCE_SETTINGS['testnet_ws_url']
            logger.info("Initialized Binance TESTNET client")
        else:
            self.client = Client(api_key, api_secret)
            self.ws_url = BINANCE_SETTINGS['live_ws_url']
            logger.info("Initialized Binance LIVE client")
        
        self.ws = None
        self.ws_thread = None
        self._ws_callbacks = {}
        
    def get_account_balance(self, asset: str = None) -> Dict:
        """
        Get account balance.
        
        Args:
            asset: Specific asset to get balance for (e.g., 'USDT', 'BTC')
            
        Returns:
            Dictionary with balance information
        """
        try:
            account = self.client.get_account()
            balances = {b['asset']: {
                'free': float(b['free']),
                'locked': float(b['locked']),
                'total': float(b['free']) + float(b['locked'])
            } for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
            
            if asset:
                return balances.get(asset, {'free': 0, 'locked': 0, 'total': 0})
            return balances
            
        except BinanceAPIException as e:
            logger.error(f"Error getting account balance: {e}")
            raise
    
    def get_ticker_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"Error getting ticker price for {symbol}: {e}")
            raise
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 500,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> pd.DataFrame:
        """
        Get historical kline/candlestick data.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1m', '5m', '1h', '1d')
            limit: Number of klines to fetch (max 1000)
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)
            
            klines = self.client.get_klines(**params)
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Keep only OHLCV columns
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            raise
    
    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        days: int = 90
    ) -> pd.DataFrame:
        """
        Get extended historical klines for backtesting.
        
        Args:
            symbol: Trading pair
            interval: Kline interval
            days: Number of days of historical data
            
        Returns:
            DataFrame with extended historical OHLCV data
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        all_klines = []
        current_start = start_time
        
        while current_start < end_time:
            df = self.get_klines(
                symbol=symbol,
                interval=interval,
                limit=1000,
                start_time=current_start
            )
            
            if df.empty:
                break
                
            all_klines.append(df)
            current_start = df.index[-1].to_pydatetime() + timedelta(minutes=1)
            time.sleep(0.1)  # Rate limiting
        
        if all_klines:
            return pd.concat(all_klines).drop_duplicates()
        return pd.DataFrame()
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get trading rules and filters for a symbol."""
        try:
            info = self.client.get_symbol_info(symbol)
            
            # Extract important filters
            filters = {}
            for f in info['filters']:
                filters[f['filterType']] = f
            
            return {
                'symbol': symbol,
                'status': info['status'],
                'base_asset': info['baseAsset'],
                'quote_asset': info['quoteAsset'],
                'base_precision': info['baseAssetPrecision'],
                'quote_precision': info['quoteAssetPrecision'],
                'min_qty': float(filters.get('LOT_SIZE', {}).get('minQty', 0)),
                'max_qty': float(filters.get('LOT_SIZE', {}).get('maxQty', 0)),
                'step_size': float(filters.get('LOT_SIZE', {}).get('stepSize', 0)),
                'min_notional': float(filters.get('NOTIONAL', {}).get('minNotional', 0)),
                'tick_size': float(filters.get('PRICE_FILTER', {}).get('tickSize', 0))
            }
        except BinanceAPIException as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            raise
    
    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Dict:
        """
        Place a market order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Amount to buy/sell
            
        Returns:
            Order response
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            logger.info(f"Market {side} order placed: {quantity} {symbol}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing market order: {e}")
            raise
    
    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Dict:
        """
        Place a limit order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Amount to buy/sell
            price: Limit price
            
        Returns:
            Order response
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price
            )
            logger.info(f"Limit {side} order placed: {quantity} {symbol} @ {price}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing limit order: {e}")
            raise
    
    def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        price: float = None
    ) -> Dict:
        """
        Place a stop-loss order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Amount to buy/sell
            stop_price: Stop trigger price
            price: Limit price (if None, uses market order at stop)
            
        Returns:
            Order response
        """
        try:
            if price:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=ORDER_TYPE_STOP_LOSS_LIMIT,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=quantity,
                    stopPrice=stop_price,
                    price=price
                )
            else:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=ORDER_TYPE_STOP_LOSS,
                    quantity=quantity,
                    stopPrice=stop_price
                )
            logger.info(f"Stop-loss order placed: {quantity} {symbol} @ stop {stop_price}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing stop-loss order: {e}")
            raise
    
    def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        price: float = None
    ) -> Dict:
        """
        Place a take-profit order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Amount to buy/sell
            stop_price: Take profit trigger price
            price: Limit price (if None, uses market order)
            
        Returns:
            Order response
        """
        try:
            if price:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=ORDER_TYPE_TAKE_PROFIT_LIMIT,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=quantity,
                    stopPrice=stop_price,
                    price=price
                )
            else:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=ORDER_TYPE_TAKE_PROFIT,
                    quantity=quantity,
                    stopPrice=stop_price
                )
            logger.info(f"Take-profit order placed: {quantity} {symbol} @ {stop_price}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing take-profit order: {e}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an open order."""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order {order_id} cancelled for {symbol}")
            return result
        except BinanceAPIException as e:
            logger.error(f"Error cancelling order: {e}")
            raise
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get all open orders."""
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol)
            return self.client.get_open_orders()
        except BinanceAPIException as e:
            logger.error(f"Error getting open orders: {e}")
            raise
    
    def start_kline_websocket(
        self,
        symbol: str,
        interval: str,
        callback: Callable
    ):
        """
        Start WebSocket stream for real-time kline data.
        
        Args:
            symbol: Trading pair (lowercase, e.g., 'btcusdt')
            interval: Kline interval
            callback: Function to call with each kline update
        """
        stream = f"{symbol.lower()}@kline_{interval}"
        self._ws_callbacks[stream] = callback
        
        def on_message(ws, message):
            data = json.loads(message)
            if 'k' in data:
                kline = data['k']
                callback({
                    'symbol': kline['s'],
                    'interval': kline['i'],
                    'timestamp': kline['t'],
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'is_closed': kline['x']
                })
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket connection closed")
        
        def on_open(ws):
            logger.info(f"WebSocket connection opened for {stream}")
        
        ws_url = f"{self.ws_url}/{stream}"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        logger.info(f"Started kline WebSocket for {symbol} {interval}")
    
    def stop_websocket(self):
        """Stop WebSocket connection."""
        if self.ws:
            self.ws.close()
            logger.info("WebSocket stopped")
    
    def round_quantity(self, symbol: str, quantity: float) -> float:
        """Round quantity to valid step size for symbol."""
        info = self.get_symbol_info(symbol)
        step_size = info['step_size']
        
        if step_size > 0:
            precision = len(str(step_size).split('.')[-1].rstrip('0'))
            return round(quantity - (quantity % step_size), precision)
        return quantity
    
    def round_price(self, symbol: str, price: float) -> float:
        """Round price to valid tick size for symbol."""
        info = self.get_symbol_info(symbol)
        tick_size = info['tick_size']
        
        if tick_size > 0:
            precision = len(str(tick_size).split('.')[-1].rstrip('0'))
            return round(price - (price % tick_size), precision)
        return price
