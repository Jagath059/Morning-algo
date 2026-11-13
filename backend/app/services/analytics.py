from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.services.session_clock import RISK_WARNING, as_ist


def categorize_gap(gap_percent: float, flat_abs: float = 0.15) -> str:
    if gap_percent >= flat_abs:
        return "gap_up"
    if gap_percent <= -flat_abs:
        return "gap_down"
    return "flat"


def gap_percent(official_open: Decimal, previous_close: Decimal) -> Decimal:
    return (official_open - previous_close) / previous_close * Decimal(100)


def opening_range(candles: list[dict], ready: bool) -> dict:
    if not ready:
        return {"status": "unavailable", "high": None, "low": None, "reason": "window_open"}
    if not candles:
        return {"status": "unavailable", "high": None, "low": None, "reason": "incomplete_candles"}
    high = max(Decimal(candle["high"]) for candle in candles)
    low = min(Decimal(candle["low"]) for candle in candles)
    return {
        "status": "ok",
        "high": f"{high.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}",
        "low": f"{low.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}",
        "reason": None,
    }


def session_vwap(candles: list[dict]) -> dict:
    weighted = Decimal(0)
    volume_sum = Decimal(0)
    for candle in candles:
        volume = Decimal(candle["volume"])
        if volume <= 0:
            continue
        typical = (Decimal(candle["high"]) + Decimal(candle["low"]) + Decimal(candle["close"])) / Decimal(3)
        weighted += typical * volume
        volume_sum += volume
    if volume_sum == 0:
        return {"status": "unavailable", "value": None, "reason": "index_volume_absent"}
    value = (weighted / volume_sum).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"status": "ok", "value": f"{value}", "reason": None}


def intraday_bias(now: datetime, range_15: dict, vwap: dict, last_price: Decimal | None, cash_open: str = "09:15") -> dict:
    local = as_ist(now)
    hour, minute = cash_open.split(":")
    open_minutes = int(hour) * 60 + int(minute)
    current_minutes = local.hour * 60 + local.minute
    if current_minutes < open_minutes:
        return {
            "trend": "neutral",
            "options_bias": "WAIT",
            "rule_id": "or15_vwap_v1",
            "explanation": "Before 09:15 IST the options label stays WAIT.",
            "risk_warning": RISK_WARNING,
        }
    if range_15.get("status") != "ok" or vwap.get("status") != "ok" or last_price is None:
        return {
            "trend": "neutral",
            "options_bias": "WAIT",
            "rule_id": "or15_vwap_v1",
            "explanation": "The 15-minute opening range or VWAP is not available, so the label stays WAIT.",
            "risk_warning": RISK_WARNING,
        }
    high = Decimal(range_15["high"])
    low = Decimal(range_15["low"])
    vwap_value = Decimal(vwap["value"])
    if last_price > high and last_price > vwap_value:
        return {
            "trend": "bullish",
            "options_bias": "CE",
            "rule_id": "or15_vwap_v1",
            "explanation": "Last price is above the 15-minute high and above VWAP.",
            "risk_warning": RISK_WARNING,
        }
    if last_price < low and last_price < vwap_value:
        return {
            "trend": "bearish",
            "options_bias": "PE",
            "rule_id": "or15_vwap_v1",
            "explanation": "Last price is below the 15-minute low and below VWAP.",
            "risk_warning": RISK_WARNING,
        }
    return {
        "trend": "neutral",
        "options_bias": "WAIT",
        "rule_id": "or15_vwap_v1",
        "explanation": "Price is inside the opening range or on the wrong side of VWAP, so the label stays WAIT.",
        "risk_warning": RISK_WARNING,
    }
