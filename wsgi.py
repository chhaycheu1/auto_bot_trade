"""
WSGI Entry Point for Production Deployment

This file is used by Gunicorn to run the Flask app in production.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import app

if __name__ == "__main__":
    app.run()
