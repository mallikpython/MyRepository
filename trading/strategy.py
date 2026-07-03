"""
Momentum signal: EMA crossover + RSI filter → bull put spread or bear call spread.
Returns a dict with direction, strikes, contracts, and reasoning.
"""

from config import (
    EMA_FAST, EMA_SLOW, RSI_PERIOD,
    RSI_OVERBOUGHT, RSI_OVERSOLD,
    TARGET_DELTA, SPREAD_WIDTH, DTE_MIN, DTE_MAX,
    MAX_RISK_PER_TRADE, MIN_CREDIT_RECEIVED, MAX_CONTRACTS,
)


def ema(prices, period):
    k = 2 / (period + 1)
    result = [prices[0]]
    for p in prices[1:]:
        result.append(p * k + result[-1] * (1 - k))
    return result


def rsi(prices, period=14):
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def determine_direction(historical_prices):
    """
    Returns 'bull', 'bear', or None (no trade).
    bull → sell put spread (profit if QQQ stays flat or rises)
    bear → sell call spread (profit if QQQ stays flat or falls)
    """
    if len(historical_prices) < EMA_SLOW + 5:
        return None, "Not enough price history"

    fast = ema(historical_prices, EMA_FAST)
    slow = ema(historical_prices, EMA_SLOW)
    current_rsi = rsi(historical_prices, RSI_PERIOD)

    ema_bullish = fast[-1] > slow[-1]
    ema_crossed_up = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
    ema_crossed_down = fast[-2] >= slow[-2] and fast[-1] < slow[-1]

    reason_parts = [
        f"EMA({EMA_FAST})={fast[-1]:.2f}",
        f"EMA({EMA_SLOW})={slow[-1]:.2f}",
        f"RSI={current_rsi:.1f}",
    ]

    if ema_bullish and current_rsi < RSI_OVERBOUGHT:
        direction = "bull"
        reason_parts.append("→ Bullish: fast EMA above slow, RSI not overbought")
    elif not ema_bullish and current_rsi > RSI_OVERSOLD:
        direction = "bear"
        reason_parts.append("→ Bearish: fast EMA below slow, RSI not oversold")
    else:
        direction = None
        reason_parts.append("→ No trade: EMA and RSI conflict")

    return direction, " | ".join(reason_parts)


def select_spread(direction, current_price, options_chain, max_risk):
    """
    Given direction and options chain data, pick the best spread strikes.
    Returns (short_strike, long_strike, contracts, credit_per_spread) or None.
    """
    if direction not in ("bull", "bear"):
        return None

    # Filter to target DTE
    valid_expirations = [
        exp for exp in options_chain
        if DTE_MIN <= exp["dte"] <= DTE_MAX
    ]
    if not valid_expirations:
        return None

    # Prefer nearest expiration for faster time decay
    expiration = min(valid_expirations, key=lambda e: e["dte"])
    option_type = "put" if direction == "bull" else "call"
    legs = [o for o in expiration["options"] if o["type"] == option_type]

    # Find short leg nearest to TARGET_DELTA
    legs_sorted = sorted(legs, key=lambda o: abs(abs(o.get("delta", 0)) - TARGET_DELTA))
    if not legs_sorted:
        return None

    short_leg = legs_sorted[0]
    short_strike = short_leg["strike"]

    if direction == "bull":
        long_strike = short_strike - SPREAD_WIDTH
    else:
        long_strike = short_strike + SPREAD_WIDTH

    long_leg = next((o for o in legs if o["strike"] == long_strike), None)
    if not long_leg:
        return None

    credit = short_leg["bid"] - long_leg["ask"]
    if credit < MIN_CREDIT_RECEIVED:
        return None

    max_loss_per_contract = (SPREAD_WIDTH - credit) * 100
    if max_loss_per_contract <= 0:
        return None

    contracts = min(
        int(max_risk / max_loss_per_contract),
        MAX_CONTRACTS,
    )
    if contracts < 1:
        return None

    return {
        "expiration": expiration["date"],
        "dte": expiration["dte"],
        "option_type": option_type,
        "short_strike": short_strike,
        "long_strike": long_strike,
        "short_delta": short_leg.get("delta"),
        "credit_per_spread": round(credit, 2),
        "max_loss_per_contract": round(max_loss_per_contract, 2),
        "contracts": contracts,
        "total_credit": round(credit * 100 * contracts, 2),
        "max_total_risk": round(max_loss_per_contract * contracts, 2),
    }
