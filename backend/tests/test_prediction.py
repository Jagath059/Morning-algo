from datetime import datetime, timezone
from decimal import Decimal

from app.services.analytics import categorize_gap, intraday_bias, session_vwap
from app.services.prediction_engine import PredictionInputs, evaluate
from app.services.session_clock import latest_completed_us_session_date, trading_date


def test_worked_example_is_green_with_locked_scores():
    result = evaluate(
        PredictionInputs(
            gift_nifty_change=0.60,
            us_session=0.30,
            asia_session=-0.20,
            india_vix_change=-1.00,
            india_vix_level=14,
        )
    )
    assert result.raw is not None
    assert f"{result.raw:.4f}" == "0.3059"
    assert result.direction == "GREEN"
    assert result.gap_up_score == "0.54"
    assert result.gap_down_score == "0.23"
    assert result.flat_score == "0.23"
    assert result.confidence == "0.75"
    assert result.score_kind == "experimental_heuristic"
    assert result.calibrated is False


def test_bearish_mirror_is_red():
    result = evaluate(
        PredictionInputs(
            gift_nifty_change=-0.60,
            us_session=-0.30,
            asia_session=0.20,
            india_vix_change=1.00,
            india_vix_level=14,
        )
    )
    assert result.direction == "RED"
    assert result.gap_down_score == "0.54"
    assert result.gap_up_score == "0.23"


def test_inside_flat_band():
    result = evaluate(PredictionInputs(gift_nifty_change=0.05, us_session=0.0, asia_session=0.0))
    assert result.direction == "FLAT"


def test_all_missing_is_unknown():
    result = evaluate(PredictionInputs())
    assert result.direction == "UNKNOWN"
    assert result.gap_up_score is None
    assert result.confidence == "0.00"
    assert result.data_quality == "none"


def test_single_feature_renormalizes_and_stale_input_is_dropped():
    fresh = evaluate(PredictionInputs(gift_nifty_change=1.0))
    stale = evaluate(PredictionInputs(gift_nifty_change=1.0, stale_features={"gift_nifty_change"}))
    assert fresh.direction == "GREEN"
    assert fresh.data_quality == "partial"
    assert stale.direction == "UNKNOWN"


def test_elevated_vix_reduces_confidence():
    calm = evaluate(PredictionInputs(gift_nifty_change=0.6, india_vix_level=14))
    hot = evaluate(PredictionInputs(gift_nifty_change=0.6, india_vix_level=22))
    assert float(hot.confidence) < float(calm.confidence)


def test_gap_edges():
    assert categorize_gap(0.15) == "gap_up"
    assert categorize_gap(-0.15) == "gap_down"
    assert categorize_gap(0.149) == "flat"
    assert categorize_gap(-0.149) == "flat"


def test_trading_date_crosses_ist_midnight():
    before = datetime(2026, 11, 12, 18, 29, 59, tzinfo=timezone.utc)
    after = datetime(2026, 11, 12, 18, 30, 0, tzinfo=timezone.utc)
    assert trading_date(before) == "2026-11-12"
    assert trading_date(after) == "2026-11-13"


def test_us_session_date_during_india_morning_and_dst():
    winter = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)  # 08:30 IST
    summer = datetime(2026, 7, 13, 3, 0, tzinfo=timezone.utc)  # 08:30 IST, US on EDT
    assert latest_completed_us_session_date(winter).isoformat() == "2026-11-12"
    assert latest_completed_us_session_date(summer).isoformat() == "2026-07-10"


def test_vwap_and_zero_volume():
    candles = [
        {"high": "10", "low": "8", "close": "9", "volume": "100"},
        {"high": "12", "low": "10", "close": "11", "volume": "100"},
    ]
    assert session_vwap(candles)["value"] == "10.00"
    assert session_vwap([{"high": "10", "low": "8", "close": "9", "volume": "0"}])["reason"] == "index_volume_absent"


def test_bias_waits_before_the_open_and_confirms_after():
    before = datetime(2026, 11, 13, 3, 44, 59, tzinfo=timezone.utc)  # 09:14 IST
    after = datetime(2026, 11, 13, 4, 0, tzinfo=timezone.utc)  # 09:30 IST
    waiting = intraday_bias(before, {"status": "ok", "high": "10", "low": "9"}, {"status": "ok", "value": "9.5"}, Decimal("11"))
    bullish = intraday_bias(after, {"status": "ok", "high": "10", "low": "9"}, {"status": "ok", "value": "9.5"}, Decimal("11"))
    assert waiting["options_bias"] == "WAIT"
    assert bullish["options_bias"] == "CE"
    assert bullish["rule_id"] == "or15_vwap_v1"
