from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
ET = ZoneInfo("America/New_York")

RISK_WARNING = (
    "This screen is decision support for the signed-in account owner. "
    "Scores are not guaranteed outcomes. CE, PE, and WAIT are labels, "
    "and this application does not place orders."
)


def _hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


@dataclass(frozen=True)
class ClockConfig:
    gift_session1_open: str = "05:15"
    preopen_start: str = "09:00"
    preopen_matching_start: str = "09:10"
    preopen_buffer_start: str = "09:12"
    cash_open: str = "09:15"
    or_15_end: str = "09:30"
    cash_close: str = "15:30"
    holidays: frozenset[str] = frozenset()


def as_ist(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("UTC"))
    return now.astimezone(IST)


def trading_date(now: datetime) -> str:
    return as_ist(now).date().isoformat()


def latest_completed_us_session_date(now: datetime) -> date:
    now_et = now.astimezone(ET) if now.tzinfo else now.replace(tzinfo=ZoneInfo("UTC")).astimezone(ET)
    close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    session = now_et.date() if now_et >= close else now_et.date() - timedelta(days=1)
    while session.weekday() >= 5:
        session -= timedelta(days=1)
    return session


def session_status(now: datetime, config: ClockConfig) -> str:
    local = as_ist(now)
    if local.weekday() >= 5:
        return "weekend"
    if local.date().isoformat() in config.holidays:
        return "closed"
    current = local.time()
    if current < _hhmm(config.gift_session1_open):
        return "pre_gift_review"
    if current < _hhmm("08:30"):
        return "gift_monitoring"
    if current < _hhmm(config.preopen_start):
        return "global_review"
    if current < _hhmm(config.cash_open):
        return "nse_preopen"
    if current < _hhmm(config.or_15_end):
        return "opening_drive"
    if current < _hhmm(config.cash_close):
        return "cash_session"
    return "closed"


def preopen_phase(now: datetime, config: ClockConfig) -> str:
    local = as_ist(now)
    current = local.time()
    if current < _hhmm(config.preopen_start) or current >= _hhmm(config.cash_close):
        return "outside"
    if current < _hhmm(config.preopen_matching_start):
        return "order_entry"
    if current < _hhmm(config.preopen_buffer_start):
        return "matching"
    if current < _hhmm(config.cash_open):
        return "buffer"
    return "continuous"


def gift_session_name(now: datetime, config: ClockConfig) -> str:
    local = as_ist(now)
    current = local.time()
    if local.weekday() == 6:
        return "closed"
    if local.weekday() == 5 and current >= _hhmm("02:45"):
        return "closed"
    if _hhmm(config.gift_session1_open) <= current < _hhmm("15:40"):
        return "session_1"
    if current >= _hhmm("16:05") or current < _hhmm("02:45"):
        return "session_2"
    return "closed"
