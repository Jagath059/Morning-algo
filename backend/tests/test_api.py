from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_preview_is_public_and_production_requires_firebase():
    from app.config import Settings

    preview = Settings(app_env="preview", firebase_project_id="")
    assert preview.auth_mode == "public-preview"
    assert preview.auth_disabled is True
    production = Settings(app_env="production", firebase_project_id="", allowed_uids="")
    try:
        production.validate_runtime()
    except RuntimeError as exc:
        assert "Firebase" in str(exc)
    else:
        raise AssertionError("production without Firebase should refuse to start")


def test_health_hides_secrets():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "Asia/Kolkata"
    assert body["checks"]["kite"] == "unconfigured"
    text = response.text.lower()
    assert "api_key" not in text
    assert "token" not in text
    assert "secret" not in text


def test_overview_is_blank_when_feeds_are_unconfigured():
    response = client.get("/api/v1/market/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["gift_nifty"]["status"] == "unavailable"
    assert body["gift_nifty"]["value"] is None
    assert body["nifty50"]["previous_close"]["value"] is None
    assert body["sensex"]["indicative_open"]["kind"] == "unavailable"


def test_latest_prediction_is_unknown_and_experimental():
    response = client.get("/api/v1/predictions/latest")
    assert response.status_code == 200
    row = response.json()["predictions"][0]
    assert row["direction"] == "UNKNOWN"
    assert row["score_kind"] == "experimental_heuristic"
    assert "gap_up_probability" not in row
    assert row["gap_up_score"] is None


def test_invalid_instrument_is_422():
    response = client.get("/api/v1/market/intraday", params={"instrument": "BANKNIFTY"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_bias_waits_and_includes_risk_warning():
    response = client.get("/api/v1/market/bias")
    assert response.status_code == 200
    body = response.json()
    assert body["options_bias"] == "WAIT"
    assert "does not place orders" in body["risk_warning"]
