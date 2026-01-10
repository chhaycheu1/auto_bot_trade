"""
Web Dashboard Runner

Run this file to start the trading bot web dashboard.

Usage:
    python dashboard.py
    
Then open http://localhost:5000 in your browser.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == '__main__':
    from web.app import app
    
    print("\n" + "=" * 50)
    print("🌐 TRADING BOT WEB DASHBOARD")
    print("=" * 50)
    print("Open in browser: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
