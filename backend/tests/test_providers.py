from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.services.providers import fetch_gift, fetch_global, fetch_kite


def _response(url: str, payload: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("GET", url))


def test_gift_quote_uses_the_configured_feed(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, timeout=None, params=None):
        seen["url"] = url
        seen["authorization"] = (headers or {}).get("Authorization", "")
        return _response(
            url,
            {"price": "24350.50", "reference": "24200.00", "as_of": "2026-11-13T02:49:50Z"},
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    settings = Settings(gift_nifty_base_url="https://feeds.example/gift", gift_nifty_api_token="gift-token")
    quote = fetch_gift(settings, datetime(2026, 11, 13, 2, 49, 55, tzinfo=timezone.utc))
    assert seen["url"] == "https://feeds.example/gift"
    assert seen["authorization"] == "Bearer gift-token"
    assert quote.status == "ok"
    assert quote.value == "24350.50"
    assert quote.source == "gift_http"
    assert quote.fixture is False


def test_old_gift_quote_is_stale(monkeypatch):
    def fake_get(url, headers=None, timeout=None, params=None):
        return _response(url, {"price": "100", "reference": "100", "as_of": "2026-11-13T02:00:00Z"})

    monkeypatch.setattr(httpx, "get", fake_get)
    settings = Settings(gift_nifty_base_url="https://feeds.example/gift", gift_stale_seconds=15)
    quote = fetch_gift(settings, datetime(2026, 11, 13, 2, 1, 0, tzinfo=timezone.utc))
    assert quote.status == "stale"
    assert quote.value == "100.00"


def test_us_quote_must_be_the_closed_session_before_the_india_open(monkeypatch):
    now = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)
    stamp = now.isoformat()

    def fake_get(url, headers=None, timeout=None, params=None):
        rows = [
            {
                "id": index_id,
                "price": "100",
                "previous_close": "99",
                "session_state": "open" if index_id == "nasdaq" else "closed",
                "session_date": "2026-11-12",
                "as_of": stamp,
            }
            for index_id in ("nasdaq", "djia", "spx", "nikkei225", "hangseng")
        ]
        return _response(url, rows)

    monkeypatch.setattr(httpx, "get", fake_get)
    settings = Settings(global_indices_base_url="https://feeds.example/world")
    quotes = fetch_global(settings, now)
    assert quotes is not None
    assert quotes["nasdaq"].status == "unavailable"
    assert quotes["nasdaq"].reason == "unexpected_session_state"
    assert quotes["nikkei225"].status == "ok"


def test_kite_without_an_access_token_does_not_call_the_network(monkeypatch):
    def fail_get(*args, **kwargs):
        raise AssertionError("Kite was called without an access token")

    monkeypatch.setattr(httpx, "get", fail_get)
    assert fetch_kite(Settings(kite_api_key="key"), datetime.now(timezone.utc)) == {}


def test_configured_gift_change_enters_the_experimental_score(monkeypatch):
    from app.services.market_state import MarketState
    from app.schemas import Quote

    quote = Quote(
        status="ok",
        value="24350.50",
        change="150.50",
        change_percent="0.6000",
        source="gift_http",
    )
    monkeypatch.setattr("app.services.market_state.fetch_gift", lambda settings, now: quote)
    monkeypatch.setattr("app.services.market_state.fetch_global", lambda settings, now: None)
    monkeypatch.setattr("app.services.market_state.fetch_kite", lambda settings, now: {})
    state = MarketState(Settings(app_env="test"))
    row = state.latest(datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc), "owner", "NIFTY50", record=False)
    assert row.predictions[0].direction == "GREEN"
    assert row.predictions[0].score_kind == "experimental_heuristic"
    assert state.history == {}
