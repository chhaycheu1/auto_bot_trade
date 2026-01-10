"""
Web Dashboard - Flask Application (Simplified)

Provides a web interface for the trading bot.
"""

from flask import Flask, render_template, jsonify, request
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TRADING_PAIRS, DEFAULT_PAIR, DEFAULT_TIMEFRAME, RISK_SETTINGS

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static'
)
app.config['SECRET_KEY'] = 'trading-bot-secret-key'

# Global state
bot_state = {
    'running': False,
    'symbol': DEFAULT_PAIR,
    'timeframe': DEFAULT_TIMEFRAME,
    'balance': 10000,
}


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', 
        pairs=TRADING_PAIRS,
        default_pair=DEFAULT_PAIR,
        timeframes=['5m', '15m', '1h', '4h'],
        default_timeframe=DEFAULT_TIMEFRAME
    )


@app.route('/api/status')
def get_status():
    """Get current bot status."""
    return jsonify(bot_state)


@app.route('/api/price/<symbol>')
def get_price(symbol):
    """Get current price and chart data."""
    try:
        from backtesting.data_loader import DataLoader
        from core.indicators import TechnicalIndicators
        
        data_loader = DataLoader()
        indicators = TechnicalIndicators()
        
        # Generate sample data for demo
        df = data_loader.generate_sample_data(
            symbol=symbol,
            interval='1h',
            days=7,
            start_price=94000 if 'BTC' in symbol else 180
        )
        
        # Calculate indicators
        df = indicators.calculate_all(df)
        
        # Get last 100 candles
        df_recent = df.tail(100)
        
        # Format for chart
        candles = []
        for idx, row in df_recent.iterrows():
            candles.append({
                'time': idx.isoformat(),
                'open': round(row['open'], 2),
                'high': round(row['high'], 2),
                'low': round(row['low'], 2),
                'close': round(row['close'], 2),
                'volume': round(row['volume'], 2)
            })
        
        # Get indicator values
        latest = df.iloc[-1]
        indicator_values = {
            'ema_short': round(float(latest['ema_short']), 2),
            'ema_medium': round(float(latest['ema_medium']), 2),
            'ema_long': round(float(latest['ema_long']), 2),
            'rsi': round(float(latest['rsi']), 2),
            'macd': round(float(latest['macd']), 4),
            'macd_signal': round(float(latest['macd_signal']), 4),
            'bb_upper': round(float(latest['bb_upper']), 2),
            'bb_middle': round(float(latest['bb_middle']), 2),
            'bb_lower': round(float(latest['bb_lower']), 2)
        }
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'price': round(float(latest['close']), 2),
            'candles': candles,
            'indicators': indicator_values
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})


@app.route('/api/signal/<symbol>')
def get_signal(symbol):
    """Get current trading signal."""
    try:
        from backtesting.data_loader import DataLoader
        from core.strategy import TradingStrategy
        from datetime import datetime
        
        data_loader = DataLoader()
        strategy = TradingStrategy()
        
        # Generate sample data
        df = data_loader.generate_sample_data(
            symbol=symbol,
            interval='1h',
            days=30,
            start_price=94000 if 'BTC' in symbol else 180
        )
        
        # Analyze
        signal, df_analyzed = strategy.analyze(df)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'signal_type': signal.signal_type.value,
            'score': round(signal.score, 1),
            'price': round(signal.price, 2),
            'timestamp': datetime.now().isoformat(),
            'details': {}
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})


@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Run a backtest with specified parameters."""
    try:
        from backtesting.backtest import Backtester
        from backtesting.data_loader import DataLoader
        
        data = request.json
        symbol = data.get('symbol', DEFAULT_PAIR)
        timeframe = data.get('timeframe', '1h')
        days = data.get('days', 90)
        
        data_loader = DataLoader()
        
        # Generate data
        df = data_loader.generate_sample_data(
            symbol=symbol,
            interval=timeframe,
            days=days,
            start_price=94000 if 'BTC' in symbol else 180
        )
        
        # Run backtest
        backtester = Backtester(initial_capital=10000)
        result = backtester.run(df, symbol, timeframe)
        
        # Format trades for display
        trades = []
        for t in result.trades[-20:]:  # Last 20 trades
            trades.append({
                'entry_time': t.entry_time.isoformat(),
                'exit_time': t.exit_time.isoformat(),
                'side': t.side,
                'entry_price': round(t.entry_price, 2),
                'exit_price': round(t.exit_price, 2),
                'pnl': round(t.pnl, 2),
                'pnl_pct': round(t.pnl_pct, 2),
                'reason': t.exit_reason
            })
        
        return jsonify({
            'success': True,
            'results': {
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': round(result.win_rate, 1),
                'profit_factor': round(result.profit_factor, 2),
                'total_return': round(result.total_return_pct, 2),
                'max_drawdown': round(result.max_drawdown_pct, 2),
                'sharpe_ratio': round(result.sharpe_ratio, 2),
                'initial_capital': result.initial_capital,
                'final_capital': round(result.final_capital, 2)
            },
            'trades': trades,
            'equity_curve': [round(v, 2) for v in result.equity_curve.tolist()[-100:]]
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🌐 TRADING BOT WEB DASHBOARD")
    print("=" * 50)
    print("Open in browser: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
