from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import (
    BiasResponse,
    ErrorBody,
    ErrorResponse,
    GiftNiftyResponse,
    GlobalIndicesResponse,
    HealthResponse,
    IntradayResponse,
    OpeningRangeResponse,
    OverviewResponse,
    PredictionList,
    PreOpenResponse,
    VwapResponse,
)
from app.services.market_state import MarketState

settings.validate_runtime()
state = MarketState(settings)
_firestore_status = "unconfigured"


def _init_firestore() -> str:
    if not settings.firebase_project_id or not settings.firebase_service_account_file:
        return "unconfigured"
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(settings.firebase_service_account_file))
        return "ok"
    except Exception as exc:
        print(f"firestore_init_failed {exc.__class__.__name__}")
        return "down"


_firestore_status = _init_firestore()
app = FastAPI(title="TradingEngineAI", version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)

_hits: dict[str, list[float]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _error(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, request_id=uuid4().hex, timestamp=_now())
    )
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


def _identity(request: Request) -> str | None:
    if settings.auth_disabled:
        return "local-dev"
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ").strip()
    if not token:
        return None
    allowlist = settings.uid_allowlist
    if allowlist and token not in allowlist:
        return ""
    return token


def _limited(uid: str) -> bool:
    now = monotonic()
    window = [stamp for stamp in _hits.get(uid, []) if now - stamp < 60]
    if len(window) >= 60:
        _hits[uid] = window
        return True
    window.append(now)
    _hits[uid] = window
    return False


def _guard(request: Request):
    uid = _identity(request)
    if uid is None:
        return None, _error(401, "UNAUTHENTICATED", "A valid Firebase ID token is required.")
    if uid == "":
        return None, _error(403, "FORBIDDEN", "This private dashboard is not enabled for this account.")
    limit_key = _client_key(request) if settings.auth_disabled else uid
    if _limited(limit_key):
        return None, _error(429, "RATE_LIMITED", "The request rate for this account is over the limit.")
    return uid, None


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    fields = ", ".join(str(err.get("loc", ["body"])[-1]) for err in exc.errors())
    return _error(422, "VALIDATION_ERROR", f"Invalid request fields: {fields}.")


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        time=_now(),
        timezone="Asia/Kolkata",
        checks={
            "process": "ok",
            "firestore": _firestore_status,
            "kite": "unconfigured" if not settings.kite_api_key else "ok",
            "gift_nifty": "unconfigured" if not settings.gift_nifty_base_url else "down",
            "global_indices": "unconfigured" if not settings.global_indices_base_url else "down",
        },
    )


@app.get("/api/v1/market/overview", response_model=OverviewResponse)
def overview(request: Request):
    _, error = _guard(request)
    if error:
        return error
    return state.overview(_now())


@app.get("/api/v1/market/gift-nifty", response_model=GiftNiftyResponse)
def gift_nifty(request: Request):
    _, error = _guard(request)
    if error:
        return error
    return state.gift(_now())


@app.get("/api/v1/market/global-indices", response_model=GlobalIndicesResponse)
def global_indices(request: Request):
    _, error = _guard(request)
    if error:
        return error
    return state.globals(_now())


@app.get("/api/v1/market/pre-open", response_model=PreOpenResponse)
def pre_open(request: Request):
    _, error = _guard(request)
    if error:
        return error
    return state.preopen(_now())


@app.get("/api/v1/predictions/latest", response_model=PredictionList)
def predictions_latest(request: Request, instrument: str | None = Query(default=None, pattern="^(NIFTY50|SENSEX)$")):
    uid, error = _guard(request)
    if error:
        return error
    return state.latest(_now(), uid or "local-dev", instrument)


@app.get("/api/v1/predictions/history", response_model=PredictionList)
def predictions_history(
    request: Request,
    instrument: str | None = Query(default=None, pattern="^(NIFTY50|SENSEX)$"),
    limit: int = Query(default=30, ge=1, le=180),
):
    uid, error = _guard(request)
    if error:
        return error
    return state.history_for(uid or "local-dev", instrument, limit)


@app.get("/api/v1/market/intraday", response_model=IntradayResponse)
def intraday(
    request: Request,
    instrument: str = Query(pattern="^(NIFTY50|SENSEX)$"),
    interval: str = Query(default="1m", pattern="^(1m|5m)$"),
):
    _, error = _guard(request)
    if error:
        return error
    return state.intraday(_now(), instrument, interval)


@app.get("/api/v1/market/opening-range", response_model=OpeningRangeResponse)
def opening_range(request: Request, instrument: str = Query(pattern="^(NIFTY50|SENSEX)$")):
    _, error = _guard(request)
    if error:
        return error
    return state.opening_range(_now(), instrument)


@app.get("/api/v1/market/vwap", response_model=VwapResponse)
def vwap(request: Request, instrument: str = Query(pattern="^(NIFTY50|SENSEX)$")):
    _, error = _guard(request)
    if error:
        return error
    return state.vwap(_now(), instrument)


@app.get("/api/v1/market/bias", response_model=BiasResponse)
def bias(request: Request):
    _, error = _guard(request)
    if error:
        return error
    return state.bias(_now())


@app.websocket("/ws/market")
async def market_socket(socket: WebSocket):
    await socket.accept()
    try:
        if not settings.auth_disabled:
            message = await socket.receive_json()
            token = message.get("token") if isinstance(message, dict) else None
            if not token or (settings.uid_allowlist and token not in settings.uid_allowlist):
                await socket.close(code=4401)
                return
        await socket.send_json(
            {
                "type": "snapshot",
                "as_of": _now().isoformat(),
                "overview": state.overview(_now()).model_dump(mode="json"),
                "prediction": state.latest(_now(), "local-dev", None).model_dump(mode="json"),
                "bias": state.bias(_now()).model_dump(mode="json"),
            }
        )
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        return
