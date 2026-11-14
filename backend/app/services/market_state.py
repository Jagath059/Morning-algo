from datetime import datetime, timezone
from decimal import Decimal
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
from app.services.providers import fetch_gift, fetch_global, fetch_kite
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
        self._kite_quotes: dict[str, Quote] = {}
        self._overview_cache: tuple[datetime, OverviewResponse] | None = None
        self._globals_cache: tuple[datetime, GlobalIndicesResponse] | None = None

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

    def _kite_reason(self) -> str:
        if not self.settings.kite_api_key:
            return "Kite is not configured."
        if not self.settings.kite_access_token:
            return "Kite API key is set. A daily access token is required before quotes can load."
        return "Kite quote was not fetched."

    def overview(self, now: datetime) -> OverviewResponse:
        if self._overview_cache and abs((now - self._overview_cache[0]).total_seconds()) < 4:
            return self._overview_cache[1]
        gift = fetch_gift(self.settings, now)
        kite = fetch_kite(self.settings, now)
        self._kite_quotes = kite
        indicative_reason = "No licensed indicative feed is configured."
        open_reason = "Cash session has not published an open."
        kite_reason = self._kite_reason()

        def previous(key: str) -> Quote:
            quote = kite.get(key)
            if quote is not None:
                return quote
            return _blank(kite_reason, "kite" if self.settings.kite_api_key else None)

        response = OverviewResponse(
            trading_date=trading_date(now),
            as_of=now.astimezone(timezone.utc),
            session_status=session_status(now, self.clock()),
            auth_mode=self.settings.auth_mode,
            gift_nifty=gift,
            nifty50=InstrumentOverview(
                previous_close=previous("nifty50"),
                indicative_open=_indicative(indicative_reason),
                official_open=_blank(open_reason),
            ),
            sensex=InstrumentOverview(
                previous_close=previous("sensex"),
                indicative_open=_indicative(indicative_reason),
                official_open=_blank(open_reason),
            ),
        )
        self._overview_cache = (now, response)
        return response

    def gift(self, now: datetime) -> GiftNiftyResponse:
        overview = self.overview(now)
        return GiftNiftyResponse(
            quote=overview.gift_nifty,
            session_name=gift_session_name(now, self.clock()),
            reference_label=None,
        )

    def globals(self, now: datetime) -> GlobalIndicesResponse:
        if self._globals_cache and abs((now - self._globals_cache[0]).total_seconds()) < 4:
            return self._globals_cache[1]
        fetched = fetch_global(self.settings, now)
        reason = "GLOBAL_INDICES_BASE_URL is not set." if fetched is None else "Global quotes were not fetched."
        indices = [
            GlobalIndex(
                id=key,
                name=name,
                session_state="unknown",
                session_date=None,
                quote=_blank(reason) if fetched is None else fetched[key],
            )
            for key, name in GLOBAL_NAMES.items()
        ]
        fresh = [row.id for row in indices if row.quote.status == "ok"]
        response = GlobalIndicesResponse(
            as_of=now.astimezone(timezone.utc),
            indices=indices,
            summary=GlobalSummary(
                text=(
                    "US and Asian quotes loaded from the configured feed."
                    if fresh
                    else f"US cash close and Asian quotes are unavailable because {reason}"
                ),
                inputs_used=fresh,
            ),
        )
        self._globals_cache = (now, response)
        return response

    def preopen(self, now: datetime) -> PreOpenResponse:
        overview = self.overview(now)
        return PreOpenResponse(
            trading_date=trading_date(now),
            phase=preopen_phase(now, self.clock()),
            nifty50=overview.nifty50.indicative_open,
            sensex=overview.sensex.indicative_open,
        )

    def _feature(self, quote: Quote | None) -> tuple[float | None, bool]:
        if quote is None or quote.change_percent is None or quote.status not in {"ok", "stale"}:
            return None, False
        return float(quote.change_percent), quote.status == "stale"

    def _mean(self, quotes: list[Quote]) -> tuple[float | None, bool]:
        fresh: list[float] = []
        stale: list[float] = []
        for quote in quotes:
            value, is_stale = self._feature(quote)
            if value is None:
                continue
            (stale if is_stale else fresh).append(value)
        if fresh:
            return sum(fresh) / len(fresh), False
        if stale:
            return sum(stale) / len(stale), True
        return None, False

    def prediction_inputs(self, now: datetime | None = None) -> PredictionInputs:
        if now is None:
            overview = None
            markets = None
            kite: dict[str, Quote] = {}
        else:
            overview = self.overview(now)
            markets = self.globals(now)
            kite = self._kite_quotes
        stale: set[str] = set()
        gift_value, gift_stale = self._feature(None if overview is None else overview.gift_nifty)
        if gift_stale:
            stale.add("gift_nifty_change")
        us_value, us_stale = (None, False)
        asia_value, asia_stale = (None, False)
        if markets is not None:
            by_id = {row.id: row.quote for row in markets.indices}
            us_value, us_stale = self._mean([by_id[key] for key in ("nasdaq", "djia", "spx") if key in by_id])
            asia_value, asia_stale = self._mean([by_id[key] for key in ("nikkei225", "hangseng") if key in by_id])
        if us_stale:
            stale.add("us_session")
        if asia_stale:
            stale.add("asia_session")
        vix = kite.get("india_vix")
        vix_change, vix_stale = self._feature(vix)
        if vix_stale:
            stale.add("india_vix_change")
        vix_level = None
        if vix is not None and vix.status == "ok" and vix.previous_reference and vix.change:
            vix_level = float(Decimal(vix.previous_reference) + Decimal(vix.change))
        return PredictionInputs(
            gift_nifty_change=gift_value,
            us_session=us_value,
            asia_session=asia_value,
            india_vix_change=vix_change,
            india_vix_level=vix_level,
            stale_features=stale,
            flat_band=self.settings.score_flat_band,
            confidence_cap=self.settings.confidence_cap_uncalibrated,
        )

    def latest(self, now: datetime, uid: str, instrument: str | None, *, record: bool = True) -> PredictionList:
        result = evaluate(self.prediction_inputs(now))
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
            if record:
                self.history.setdefault(uid, []).append(row)
        return PredictionList(predictions=rows)

    def history_for(self, uid: str, instrument: str | None, limit: int) -> PredictionList:
        rows = self.history.get(uid, [])
        if instrument:
            rows = [row for row in rows if row.instrument == instrument]
        return PredictionList(predictions=list(reversed(rows[-limit:])))

    def _candle_reason(self) -> str:
        if not self.settings.kite_api_key:
            return "Kite is not configured."
        if not self.settings.kite_access_token:
            return "A daily Kite access token is required before candles can load."
        return "Kite candles are not loaded yet."

    def intraday(self, now: datetime, instrument: str, interval: str) -> IntradayResponse:
        reason = self._candle_reason()
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
        reason = self._candle_reason()
        window = RangeWindow(status="unavailable", reason=reason)
        return OpeningRangeResponse(
            instrument=instrument,
            trading_date=trading_date(now),
            range_5m=window,
            range_15m=window,
        )

    def vwap(self, now: datetime, instrument: str) -> VwapResponse:
        reason = self._candle_reason()
        return VwapResponse(
            instrument=instrument,
            trading_date=trading_date(now),
            status="unavailable",
            reason=reason,
        )

    def bias(self, now: datetime) -> BiasResponse:
        payload = intraday_bias(now, {"status": "unavailable"}, {"status": "unavailable"}, None, self.settings.cash_open)
        return BiasResponse(as_of=now.astimezone(timezone.utc), **payload)
