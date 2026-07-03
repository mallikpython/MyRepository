"""
QQQ Options Automated Trader
Usage: python trader.py [--dry-run]

Requires: pip install robin_stocks pandas requests
Set env vars: ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD (or use .env file)
"""

import os
import sys
import csv
import json
import logging
import argparse
from datetime import datetime, date

import robin_stocks.robinhood as rh
import pandas as pd

from config import (
    SYMBOL, MAX_RISK_PER_TRADE, MAX_DAILY_LOSS,
    PROFIT_TARGET_PCT, STOP_LOSS_PCT, LOG_FILE,
)
from strategy import determine_direction, select_spread

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("trading/trader.log")],
)
log = logging.getLogger(__name__)


def login():
    username = os.environ.get("ROBINHOOD_USERNAME")
    password = os.environ.get("ROBINHOOD_PASSWORD")
    if not username or not password:
        raise EnvironmentError(
            "Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD environment variables."
        )
    rh.login(username, password, expiresIn=86400, store_session=False)
    log.info("Logged in to Robinhood")


def get_historical_prices(symbol, days=60):
    data = rh.stocks.get_stock_historicals(
        symbol, interval="day", span="3month", bounds="regular"
    )
    closes = [float(d["close_price"]) for d in data if d["close_price"]]
    log.info(f"Fetched {len(closes)} days of {symbol} price history")
    return closes


def get_options_chain(symbol):
    """Build a simplified options chain from Robinhood data."""
    today = date.today()
    expirations = rh.options.get_chains(symbol)
    if not expirations:
        return []

    chain = []
    for exp_date_str in expirations.get("expiration_dates", []):
        exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        options_data = rh.options.find_options_by_expiration(symbol, exp_date_str)
        if not options_data:
            continue
        legs = []
        for o in options_data:
            try:
                legs.append({
                    "strike": float(o["strike_price"]),
                    "type": o["type"],
                    "bid": float(o.get("bid_price") or 0),
                    "ask": float(o.get("ask_price") or 0),
                    "delta": float(o.get("delta") or 0),
                    "option_id": o["id"],
                })
            except (TypeError, ValueError):
                continue
        chain.append({"date": exp_date_str, "dte": dte, "options": legs})

    return chain


def check_daily_loss():
    """Return cumulative P&L from today's log entries."""
    if not os.path.exists(LOG_FILE):
        return 0.0
    total = 0.0
    with open(LOG_FILE) as f:
        for row in csv.DictReader(f):
            if row.get("date") == str(date.today()):
                total += float(row.get("realized_pnl", 0))
    return total


def log_trade(trade_info):
    fieldnames = [
        "date", "time", "symbol", "direction", "expiration", "dte",
        "short_strike", "long_strike", "contracts", "credit_per_spread",
        "total_credit", "max_total_risk", "order_id", "realized_pnl", "notes",
    ]
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(trade_info)


def place_spread(direction, spread, dry_run=False):
    """Place the two-leg spread order."""
    symbol = SYMBOL
    exp = spread["expiration"]
    short_s = str(spread["short_strike"])
    long_s = str(spread["long_strike"])
    otype = spread["option_type"]
    qty = spread["contracts"]
    credit = spread["credit_per_spread"]

    log.info(
        f"{'[DRY RUN] ' if dry_run else ''}Placing {'bull put' if direction == 'bull' else 'bear call'} "
        f"spread: {qty}x {exp} {otype} {short_s}/{long_s} @ ${credit:.2f} credit"
    )

    if dry_run:
        return {"id": "DRY_RUN", "state": "simulated"}

    # Build Robinhood multi-leg order
    legs = [
        {
            "expirationDate": exp,
            "strike": short_s,
            "optionType": otype,
            "effect": "open",
            "action": "sell",
        },
        {
            "expirationDate": exp,
            "strike": long_s,
            "optionType": otype,
            "effect": "open",
            "action": "buy",
        },
    ]

    order = rh.orders.order_option_spread(
        direction="credit",
        price=credit,
        symbol=symbol,
        quantity=qty,
        legs=legs,
    )
    return order


def main():
    parser = argparse.ArgumentParser(description="QQQ Options Spread Trader")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without placing real orders")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info(f"QQQ Options Trader starting  {'[DRY RUN]' if args.dry_run else '[LIVE]'}")
    log.info("=" * 60)

    # ── Guard: daily loss limit ────────────────────────────────────────────────
    daily_pnl = check_daily_loss()
    if daily_pnl <= -MAX_DAILY_LOSS:
        log.warning(f"Daily loss limit hit (${-daily_pnl:.2f}). No new trades today.")
        sys.exit(0)

    if not args.dry_run:
        login()

    # ── Fetch data ─────────────────────────────────────────────────────────────
    prices = get_historical_prices(SYMBOL)
    current_price = prices[-1]
    log.info(f"{SYMBOL} current price: ${current_price:.2f}")

    # ── Signal ────────────────────────────────────────────────────────────────
    direction, reason = determine_direction(prices)
    log.info(f"Signal: {direction or 'NONE'}  |  {reason}")

    if direction is None:
        log.info("No trade signal today. Exiting.")
        log_trade({
            "date": str(date.today()),
            "time": datetime.now().strftime("%H:%M"),
            "symbol": SYMBOL,
            "direction": "none",
            "notes": reason,
        })
        return

    # ── Options chain ─────────────────────────────────────────────────────────
    if args.dry_run:
        log.info("[DRY RUN] Skipping live options chain fetch; using mock data")
        chain = [{
            "date": "2024-12-06",
            "dte": 3,
            "options": [
                {"strike": current_price - 2, "type": "put", "bid": 1.10, "ask": 1.15, "delta": -0.30, "option_id": "a"},
                {"strike": current_price - 4, "type": "put", "bid": 0.55, "ask": 0.60, "delta": -0.18, "option_id": "b"},
                {"strike": current_price + 2, "type": "call", "bid": 1.10, "ask": 1.15, "delta": 0.30, "option_id": "c"},
                {"strike": current_price + 4, "type": "call", "bid": 0.55, "ask": 0.60, "delta": 0.18, "option_id": "d"},
            ],
        }]
    else:
        chain = get_options_chain(SYMBOL)

    # ── Select spread ─────────────────────────────────────────────────────────
    spread = select_spread(direction, current_price, chain, MAX_RISK_PER_TRADE)

    if spread is None:
        log.warning("No suitable spread found (chain too thin or credit too low). No trade.")
        return

    log.info(
        f"Selected spread: {spread['contracts']}x {spread['expiration']} "
        f"{spread['option_type']} {spread['short_strike']}/{spread['long_strike']} "
        f"| Credit: ${spread['credit_per_spread']:.2f} | Max risk: ${spread['max_total_risk']:.2f}"
    )

    # ── Place order ───────────────────────────────────────────────────────────
    order = place_spread(direction, spread, dry_run=args.dry_run)
    order_id = order.get("id", "unknown") if order else "failed"
    log.info(f"Order result: id={order_id}  state={order.get('state', '?') if order else 'error'}")

    # ── Log trade ─────────────────────────────────────────────────────────────
    log_trade({
        "date": str(date.today()),
        "time": datetime.now().strftime("%H:%M"),
        "symbol": SYMBOL,
        "direction": direction,
        "expiration": spread["expiration"],
        "dte": spread["dte"],
        "short_strike": spread["short_strike"],
        "long_strike": spread["long_strike"],
        "contracts": spread["contracts"],
        "credit_per_spread": spread["credit_per_spread"],
        "total_credit": spread["total_credit"],
        "max_total_risk": spread["max_total_risk"],
        "order_id": order_id,
        "realized_pnl": 0,
        "notes": reason,
    })

    log.info("Done.")


if __name__ == "__main__":
    main()
