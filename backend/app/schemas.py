from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    ok = "ok"
    stale = "stale"
    unavailable = "unavailable"


class Quote(BaseModel):
    status: DataStatus
    value: str | None = None
    previous_reference: str | None = None
    change: str | None = None
    change_percent: str | None = None
    as_of: datetime | None = None
    source: str | None = None
    reason: str | None = None
    fixture: bool = False


class IndicativeOpen(BaseModel):
    status: DataStatus
    value: str | None = None
    kind: str = "unavailable"
    as_of: datetime | None = None
    source: str | None = None
    reason: str | None = None
    fixture: bool = False


class InstrumentOverview(BaseModel):
    previous_close: Quote
    indicative_open: IndicativeOpen
    official_open: Quote


class OverviewResponse(BaseModel):
    trading_date: str
    as_of: datetime
    session_status: str
    auth_mode: str
    gift_nifty: Quote
    nifty50: InstrumentOverview
    sensex: InstrumentOverview


class GiftNiftyResponse(BaseModel):
    quote: Quote
    session_name: str
    reference_label: str | None = None


class GlobalIndex(BaseModel):
    id: str
    name: str
    session_state: str
    session_date: str | None = None
    quote: Quote


class GlobalSummary(BaseModel):
    text: str
    score_kind: str = "descriptive"
    inputs_used: list[str] = Field(default_factory=list)


class GlobalIndicesResponse(BaseModel):
    as_of: datetime
    indices: list[GlobalIndex]
    summary: GlobalSummary


class PreOpenResponse(BaseModel):
    trading_date: str
    phase: str
    nifty50: IndicativeOpen
    sensex: IndicativeOpen


class ExplanationItem(BaseModel):
    feature: str
    contribution: str
    note: str


class Prediction(BaseModel):
    prediction_id: str
    trading_date: str
    instrument: str
    direction: str
    gap_up_score: str | None
    gap_down_score: str | None
    flat_score: str | None
    score_kind: str
    calibrated: bool
    confidence: str
    confidence_meaning: str
    model_version: str
    data_quality: str
    explanation: list[ExplanationItem]
    created_at: datetime
    inputs_as_of: datetime | None = None


class PredictionList(BaseModel):
    predictions: list[Prediction]


class Candle(BaseModel):
    time: datetime
    open: str
    high: str
    low: str
    close: str
    volume: str


class IntradayResponse(BaseModel):
    instrument: str
    interval: str
    trading_date: str
    source: str | None
    candles: list[Candle]
    status: DataStatus
    reason: str | None = None


class RangeWindow(BaseModel):
    status: DataStatus
    high: str | None = None
    low: str | None = None
    ready_at: datetime | None = None
    reason: str | None = None


class OpeningRangeResponse(BaseModel):
    instrument: str
    trading_date: str
    range_5m: RangeWindow
    range_15m: RangeWindow


class VwapResponse(BaseModel):
    instrument: str
    trading_date: str
    status: DataStatus
    value: str | None = None
    reason: str | None = None


class BiasResponse(BaseModel):
    trend: str
    options_bias: str
    rule_id: str
    explanation: str
    risk_warning: str
    as_of: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    time: datetime
    timezone: str
    checks: dict[str, str]


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: ErrorBody
