"""
Logging Module

Provides consistent logging across the application.
"""

import logging
import sys
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for Windows
init()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


def get_logger(name: str, level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    Get a configured logger.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(file_handler)
    
    return logger


def log_trade(logger: logging.Logger, trade_type: str, symbol: str, 
              price: float, quantity: float, **kwargs):
    """Log a trade with formatted output."""
    emoji = "🟢" if trade_type == "BUY" else "🔴"
    logger.info(
        f"{emoji} {trade_type} | {symbol} | "
        f"Price: {price:.2f} | Qty: {quantity:.6f} | "
        f"{' | '.join(f'{k}: {v}' for k, v in kwargs.items())}"
    )


def log_signal(logger: logging.Logger, signal_type: str, symbol: str,
               score: float, price: float):
    """Log a trading signal."""
    emoji = "📈" if signal_type == "BUY" else "📉" if signal_type == "SELL" else "⏸️"
    logger.info(
        f"{emoji} {signal_type} Signal | {symbol} | "
        f"Score: {score:.1f}% | Price: {price:.2f}"
    )
