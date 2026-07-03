"""
QQQ Options Trading System - Configuration
Adjust these values to match your risk tolerance and account size.
"""

# ── Risk Management ────────────────────────────────────────────────────────────
MAX_RISK_PER_TRADE = 300        # Max dollars to risk per spread (width * 100 * contracts)
MAX_DAILY_LOSS = 500            # Stop trading for the day if cumulative loss hits this
MIN_CREDIT_RECEIVED = 0.30     # Minimum credit per spread (filters bad fills)
MAX_CONTRACTS = 5              # Hard cap on contracts per trade

# ── Spread Settings ────────────────────────────────────────────────────────────
SPREAD_WIDTH = 2.0             # Dollar width between long/short strikes (e.g. 2 points)
TARGET_DELTA = 0.30            # Short leg target delta (0.25–0.35 is common for credit spreads)
DTE_MIN = 1                    # Minimum days-to-expiration to consider
DTE_MAX = 5                    # Maximum days-to-expiration to consider (prefer weekly)

# ── Momentum Signal ────────────────────────────────────────────────────────────
EMA_FAST = 9                   # Fast EMA period (days)
EMA_SLOW = 21                  # Slow EMA period (days)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 65            # Don't sell puts above this RSI (too extended)
RSI_OVERSOLD = 35              # Don't sell calls below this RSI

# ── Trade Management ───────────────────────────────────────────────────────────
PROFIT_TARGET_PCT = 0.50       # Close spread at 50% of max profit
STOP_LOSS_PCT = 2.0            # Close spread at 2x credit received (200% loss)

# ── Account / Symbol ──────────────────────────────────────────────────────────
SYMBOL = "QQQ"

# Paths anchored to this directory so the trader works from any working directory
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(_HERE, "trade_log.csv")
APP_LOG_FILE = os.path.join(_HERE, "trader.log")
