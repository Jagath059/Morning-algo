from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from math import exp

WEIGHTS = {
    "gift_nifty_change": 0.40,
    "us_session": 0.25,
    "asia_session": 0.15,
    "preopen_indicative": 0.12,
    "india_vix_change": 0.05,
    "overnight_event": 0.03,
}
SCALES = {
    "gift_nifty_change": 1.0,
    "us_session": 1.5,
    "asia_session": 1.5,
    "preopen_indicative": 1.0,
    "india_vix_change": 5.0,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())


@dataclass
class PredictionInputs:
    gift_nifty_change: float | None = None
    us_session: float | None = None
    asia_session: float | None = None
    india_vix_change: float | None = None
    india_vix_level: float | None = None
    preopen_indicative: float | None = None
    overnight_event: str | None = None
    stale_features: set[str] = field(default_factory=set)
    flat_band: float = 0.15
    confidence_cap: float = 0.75


@dataclass
class ScoreResult:
    direction: str
    raw: float | None
    gap_up_score: str | None
    gap_down_score: str | None
    flat_score: str | None
    confidence: str
    data_quality: str
    explanation: list[dict[str, str]]
    score_kind: str = "experimental_heuristic"
    calibrated: bool = False
    model_version: str = "heuristic-1"
    confidence_meaning: str = "feature_coverage_and_freshness"


def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def _shares(raw: float) -> tuple[str, str, str]:
    temperature = 0.75
    parts = (
        exp(raw / temperature),
        exp(-raw / temperature),
        exp(-abs(raw) / temperature),
    )
    total = sum(parts)
    rounded = [
        Decimal(part / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for part in parts
    ]
    drift = Decimal("1.00") - sum(rounded, Decimal("0"))
    if drift != 0:
        # Adjust the largest share. Equal shares break toward gap-up, then gap-down, then flat.
        target = max(range(3), key=lambda index: (rounded[index], -index))
        rounded[target] = (rounded[target] + drift).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (_money(rounded[0]), _money(rounded[1]), _money(rounded[2]))


def _note(feature: str, unit: float, raw_value: float | str) -> str:
    if feature == "gift_nifty_change":
        return f"GIFT Nifty {raw_value:+.2f}% versus its configured reference."
    if feature == "us_session":
        return f"Latest completed US cash session averages {raw_value:+.2f}%."
    if feature == "asia_session":
        return f"Asian session averages {raw_value:+.2f}%."
    if feature == "preopen_indicative":
        return f"Licensed indicative gap is {raw_value:+.2f}% versus the previous close."
    if feature == "india_vix_change":
        return f"India VIX change is {raw_value:+.2f}%."
    if feature == "overnight_event":
        return f"Overnight flag is {raw_value}."
    return f"{feature} unit {unit:.2f}."


def evaluate(inputs: PredictionInputs) -> ScoreResult:
    numeric = {
        "gift_nifty_change": inputs.gift_nifty_change,
        "us_session": inputs.us_session,
        "asia_session": inputs.asia_session,
        "preopen_indicative": inputs.preopen_indicative,
        "india_vix_change": inputs.india_vix_change,
    }
    present: list[tuple[str, float, float]] = []
    stale_excluded = False
    for feature, value in numeric.items():
        if feature in inputs.stale_features:
            stale_excluded = True
            continue
        if value is None:
            continue
        unit = _clip(value / SCALES[feature])
        present.append((feature, unit, value))

    if inputs.overnight_event in {"risk_on", "risk_off"} and "overnight_event" not in inputs.stale_features:
        unit = 1.0 if inputs.overnight_event == "risk_on" else -1.0
        present.append(("overnight_event", unit, inputs.overnight_event))

    if not present:
        return ScoreResult(
            direction="UNKNOWN",
            raw=None,
            gap_up_score=None,
            gap_down_score=None,
            flat_score=None,
            confidence="0.00",
            data_quality="none",
            explanation=[],
        )

    weight_sum = sum(WEIGHTS[feature] for feature, _, _ in present)
    raw = sum(WEIGHTS[feature] * unit for feature, unit, _ in present) / weight_sum
    if raw >= inputs.flat_band:
        direction = "GREEN"
    elif raw <= -inputs.flat_band:
        direction = "RED"
    else:
        direction = "FLAT"

    coverage = weight_sum / TOTAL_WEIGHT
    confidence = min(inputs.confidence_cap, 0.20 + 0.70 * coverage)
    if inputs.india_vix_level is not None and "india_vix_level" not in inputs.stale_features and inputs.india_vix_level >= 20:
        confidence *= 0.85
    if stale_excluded:
        confidence *= 0.90
    confidence = max(0.0, confidence)

    up, down, flat = _shares(raw)
    explanation = []
    for feature, unit, value in present:
        contribution = WEIGHTS[feature] * unit / weight_sum
        explanation.append(
            {
                "feature": feature,
                "contribution": f"{contribution:.2f}",
                "note": _note(feature, unit, value),
            }
        )
    quality = "full" if len(present) == len(WEIGHTS) else "partial"
    return ScoreResult(
        direction=direction,
        raw=raw,
        gap_up_score=up,
        gap_down_score=down,
        flat_score=flat,
        confidence=f"{confidence:.2f}",
        data_quality=quality,
        explanation=explanation,
    )
