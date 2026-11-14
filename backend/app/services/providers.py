"""Licensed HTTP adapters. Unconfigured feeds do not call the network."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

from app.config import Settings
from app.schemas import Quote
from app.services.session_clock import as_ist

GIFT_SOURCE = "gift_http"
GLOBAL_SOURCE = "global_http"
KITE_SOURCE = "kite"
KITE_QUOTE_URL = "https://api.kite.trade/quote"
US_IDS = {"nasdaq", "djia", "spx"}
INDEX_IDS = ("nasdaq", "djia", "spx", "nikkei225", "hangseng")
KITE_SYMBOLS = {
    "nifty50": "NSE:NIFTY 50",
    "sensex": "BSE:SENSEX",
    "india_vix": "NSE:INDIA VIX",
}


def _blank(reason: str, source: str | None = None) -> Quote:
    return Quote(status="unavailable", value=None, reason=reason, source=source)


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


def _stamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _quote_from_pair(
    price: Decimal,
    reference: Decimal | None,
    as_of: datetime,
    source: str,
    stale: bool,
) -> Quote:
    change = None if reference is None else price - reference
    percent = None
    if reference not in (None, 0) and change is not None:
        percent = (change / reference) * Decimal(100)
    return Quote(
        status="stale" if stale else "ok",
        value=f"{price:.2f}",
        previous_reference=None if reference is None else f"{reference:.2f}",
        change=None if change is None else f"{change:.2f}",
        change_percent=None if percent is None else f"{percent:.4f}",
        as_of=as_of,
        source=source,
        reason="Quote is older than the freshness limit." if stale else None,
    )


def _get_json(url: str, token: str) -> tuple[object | None, str | None]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.get(url, headers=headers, timeout=3.0)
        response.raise_for_status()
        return response.json(), None
    except httpx.HTTPError:
        return None, "The feed request failed."
    except ValueError:
        return None, "The feed did not return JSON."


def fetch_gift(settings: Settings, now: datetime) -> Quote:
    if not settings.gift_nifty_base_url:
        return _blank("GIFT_NIFTY_BASE_URL is not set.")
    payload, error = _get_json(settings.gift_nifty_base_url, settings.gift_nifty_api_token)
    if error or not isinstance(payload, dict):
        return _blank(error or "GIFT quote was not fetched.", GIFT_SOURCE)
    price = _decimal(payload.get("price"))
    reference = _decimal(payload.get("reference"))
    as_of = _stamp(payload.get("as_of"))
    if price is None or as_of is None:
        return _blank("GIFT quote was missing a numeric price or as_of.", GIFT_SOURCE)
    age = (now.astimezone(timezone.utc) - as_of).total_seconds()
    return _quote_from_pair(price, reference, as_of, GIFT_SOURCE, age > settings.gift_stale_seconds)


def fetch_global(settings: Settings, now: datetime) -> dict[str, Quote] | None:
    """None means the feed is not configured. A dict always contains the five ids."""
    if not settings.global_indices_base_url:
        return None
    payload, error = _get_json(settings.global_indices_base_url, settings.global_indices_api_token)
    rows = payload if isinstance(payload, list) else []
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)}
    local = as_ist(now)
    require_us_closed = local.weekday() < 5 and local.strftime("%H:%M") < settings.cash_open
    quotes: dict[str, Quote] = {}
    for index_id in INDEX_IDS:
        row = by_id.get(index_id)
        if error or row is None:
            quotes[index_id] = _blank(error or "This index was missing from the feed.", GLOBAL_SOURCE)
            continue
        if index_id in US_IDS and require_us_closed and row.get("session_state") != "closed":
            quotes[index_id] = _blank("unexpected_session_state", GLOBAL_SOURCE)
            continue
        price = _decimal(row.get("price"))
        reference = _decimal(row.get("previous_close"))
        as_of = _stamp(row.get("as_of"))
        if price is None or as_of is None:
            quotes[index_id] = _blank("Global quote was missing a numeric price or as_of.", GLOBAL_SOURCE)
            continue
        age = (now.astimezone(timezone.utc) - as_of).total_seconds()
        limit = settings.asia_stale_seconds if index_id not in US_IDS else None
        quotes[index_id] = _quote_from_pair(
            price,
            reference,
            as_of,
            GLOBAL_SOURCE,
            limit is not None and age > limit,
        )
    return quotes


def fetch_kite(settings: Settings, now: datetime) -> dict[str, Quote]:
    """Previous-close quotes for Nifty, Sensex, and India VIX. Empty when Kite cannot be called."""
    if not settings.kite_api_key or not settings.kite_access_token:
        return {}
    headers = {
        "Authorization": f"token {settings.kite_api_key}:{settings.kite_access_token}",
        "X-Kite-Version": "3",
    }
    try:
        response = httpx.get(
            KITE_QUOTE_URL,
            params=[("i", symbol) for symbol in KITE_SYMBOLS.values()],
            headers=headers,
            timeout=3.0,
        )
    except httpx.HTTPError:
        return {key: _blank("Kite quote was not fetched.", KITE_SOURCE) for key in KITE_SYMBOLS}
    if response.status_code in {401, 403}:
        reason = "Kite rejected the access token."
        try:
            message = str(response.json().get("message", "")).lower()
        except ValueError:
            message = ""
        if "permission" in message or "insufficient" in message:
            reason = "kite_plan_lacks_market_data"
        return {key: _blank(reason, KITE_SOURCE) for key in KITE_SYMBOLS}
    try:
        body = response.json()
    except ValueError:
        return {key: _blank("Kite quote was not fetched.", KITE_SOURCE) for key in KITE_SYMBOLS}
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return {key: _blank("Kite quote was not fetched.", KITE_SOURCE) for key in KITE_SYMBOLS}
    quotes: dict[str, Quote] = {}
    for key, symbol in KITE_SYMBOLS.items():
        row = data.get(symbol)
        if not isinstance(row, dict):
            quotes[key] = _blank("Kite did not return this instrument.", KITE_SOURCE)
            continue
        ohlc = row.get("ohlc") if isinstance(row.get("ohlc"), dict) else {}
        reference = _decimal(ohlc.get("close"))
        last = _decimal(row.get("last_price"))
        price = reference if reference is not None else last
        if price is None:
            quotes[key] = _blank("Kite quote had no price.", KITE_SOURCE)
            continue
        as_of = _stamp(row.get("timestamp")) or now.astimezone(timezone.utc)
        quotes[key] = _quote_from_pair(price, reference, as_of, KITE_SOURCE, False)
        if last is not None and reference not in (None, 0):
            change = last - reference
            percent = (change / reference) * Decimal(100)
            quotes[key].change = f"{change:.2f}"
            quotes[key].change_percent = f"{percent:.4f}"
    return quotes
