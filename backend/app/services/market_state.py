from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from app.schemas import (
    BiasResponse,
    GiftNiftyResponse,
    GlobalIndex,
    GlobalIndicesResponse,
    GlobalSummary,
    IndicativeOpen,
    InstrumentOverview,
    IntradayResponse,
    OpeningRangeResponse,
    OverviewResponse,
    Prediction,
    PredictionList,
    PreOpenResponse,
    Quote,
    RangeWindow,
    VwapResponse,
)
from app.services.analytics import intraday_bias
from app.services.prediction_engine import PredictionInputs, evaluate
from app.services.session_clock import ClockConfig, gift_session_name, preopen_phase, session_status, trading_date

GLOBAL_NAMES = {
    "nasdaq": "Nasdaq",
    "djia": "Dow Jones",
    "spx": "S&P 500",
    "nikkei225": "Nikkei 225",
    "hangseng": "Hang Seng",
}


def _blank(reason: str, source: str | None = None) -> Quote:
    return Quote(status="unavailable", value=None, reason=reason, source=source)


def _indicative(reason: str) -> IndicativeOpen:
    return IndicativeOpen(status="unavailable", value=None, kind="unavailable", reason=reason)


class MarketState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.history: dict[str, list[Prediction]] = {}

    def clock(self) -> ClockConfig:
        return ClockConfig(
            gift_session1_open=self.settings.gift_session1_open,
            preopen_start=self.settings.preopen_start,
            preopen_matching_start=self.settings.preopen_matching_start,
            preopen_buffer_start=self.settings.preopen_buffer_start,
            cash_open=self.settings.cash_open,
            or_15_end=self.settings.or_15_end,
            cash_close=self.settings.cash_close,
            holidays=frozenset(self.settings.holidays),
        )

    def overview(self, now: datetime) -> OverviewResponse:
        gift_reason = "GIFT_NIFTY_BASE_URL is not set." if not self.settings.gift_nifty_base_url else "GIFT quote was not fetched."
        kite_reason = "Kite is not configured." if not self.settings.kite_api_key else "Kite quote was not fetched."
        indicative_reason = "No licensed indicative feed is configured."
        open_reason = "Cash session has not published an open."
        return OverviewResponse(
            trading_date=trading_date(now),
            as_of=now.astimezone(timezone.utc),
            session_status=session_status(now, self.clock()),
            auth_mode=self.settings.auth_mode,
            gift_nifty=_blank(gift_reason, "gift_http" if self.settings.gift_nifty_base_url else None),
            nifty50=InstrumentOverview(
                previous_close=_blank(kite_reason, "kite" if self.settings.kite_api_key else None),
                indicative_open=_indicative(indicative_reason),
                official_open=_blank(open_reason),
            ),
            sensex=InstrumentOverview(
                previous_close=_blank(kite_reason, "kite" if self.settings.kite_api_key else None),
                indicative_open=_indicative(indicative_reason),
                official_open=_blank(open_reason),
            ),
        )

    def gift(self, now: datetime) -> GiftNiftyResponse:
        overview = self.overview(now)
        return GiftNiftyResponse(
            quote=overview.gift_nifty,
            session_name=gift_session_name(now, self.clock()),
            reference_label=None,
        )

    def globals(self, now: datetime) -> GlobalIndicesResponse:
        reason = "GLOBAL_INDICES_BASE_URL is not set." if not self.settings.global_indices_base_url else "Global quotes were not fetched."
        indices = [
            GlobalIndex(
                id=key,
                name=name,
                session_state="unknown",
                session_date=None,
                quote=_blank(reason),
            )
            for key, name in GLOBAL_NAMES.items()
        ]
        return GlobalIndicesResponse(
            as_of=now.astimezone(timezone.utc),
            indices=indices,
            summary=GlobalSummary(
                text=f"US cash close and Asian quotes are unavailable because {reason}",
                inputs_used=[],
            ),
        )

    def preopen(self, now: datetime) -> PreOpenResponse:
        overview = self.overview(now)
        return PreOpenResponse(
            trading_date=trading_date(now),
            phase=preopen_phase(now, self.clock()),
            nifty50=overview.nifty50.indicative_open,
            sensex=overview.sensex.indicative_open,
        )

    def prediction_inputs(self) -> PredictionInputs:
        return PredictionInputs(
            flat_band=self.settings.score_flat_band,
            confidence_cap=self.settings.confidence_cap_uncalibrated,
        )

    def latest(self, now: datetime, uid: str, instrument: str | None) -> PredictionList:
        result = evaluate(self.prediction_inputs())
        created = now.astimezone(timezone.utc)
        instruments = [instrument] if instrument else ["NIFTY50", "SENSEX"]
        rows = []
        for name in instruments:
            explanation = list(result.explanation)
            if name == "SENSEX" and result.direction != "UNKNOWN":
                explanation.append(
                    {
                        "feature": "sensex_scope",
                        "contribution": "0.00",
                        "note": "Sensex-specific pre-open input was unavailable.",
                    }
                )
            row = Prediction(
                prediction_id=str(uuid4()),
                trading_date=trading_date(now),
                instrument=name,
                direction=result.direction,
                gap_up_score=result.gap_up_score,
                gap_down_score=result.gap_down_score,
                flat_score=result.flat_score,
                score_kind=result.score_kind,
                calibrated=result.calibrated,
                confidence=result.confidence,
                confidence_meaning=result.confidence_meaning,
                model_version=result.model_version,
                data_quality=result.data_quality,
                explanation=explanation,
                created_at=created,
                inputs_as_of=created,
            )
            rows.append(row)
            self.history.setdefault(uid, []).append(row)
        return PredictionList(predictions=rows)

    def history_for(self, uid: str, instrument: str | None, limit: int) -> PredictionList:
        rows = self.history.get(uid, [])
        if instrument:
            rows = [row for row in rows if row.instrument == instrument]
        return PredictionList(predictions=list(reversed(rows[-limit:])))

    def intraday(self, now: datetime, instrument: str, interval: str) -> IntradayResponse:
        reason = "kite_plan_lacks_market_data" if self.settings.kite_api_key else "Kite is not configured."
        return IntradayResponse(
            instrument=instrument,
            interval=interval,
            trading_date=trading_date(now),
            source="kite" if self.settings.kite_api_key else None,
            candles=[],
            status="unavailable",
            reason=reason,
        )

    def opening_range(self, now: datetime, instrument: str) -> OpeningRangeResponse:
        reason = "Kite is not configured." if not self.settings.kite_api_key else "incomplete_candles"
        window = RangeWindow(status="unavailable", reason=reason)
        return OpeningRangeResponse(
            instrument=instrument,
            trading_date=trading_date(now),
            range_5m=window,
            range_15m=window,
        )

    def vwap(self, now: datetime, instrument: str) -> VwapResponse:
        reason = "Kite is not configured." if not self.settings.kite_api_key else "index_volume_absent"
        return VwapResponse(
            instrument=instrument,
            trading_date=trading_date(now),
            status="unavailable",
            reason=reason,
        )

    def bias(self, now: datetime) -> BiasResponse:
        payload = intraday_bias(now, {"status": "unavailable"}, {"status": "unavailable"}, None, self.settings.cash_open)
        return BiasResponse(as_of=now.astimezone(timezone.utc), **payload)
