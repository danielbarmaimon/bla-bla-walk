"""Fixed city daily means; bounded noncommercial forecast fallback for colours."""

import json
from datetime import UTC, datetime, timedelta
from threading import Lock

import httpx

from ..interfaces import PaletteForecast, Provenance
from .addresses import ROOT

SETTINGS = json.loads((ROOT / "config/palette-forecast.json").read_text())
PATH = ROOT / ".cache/palette-forecast.json"
LOCK = Lock()
NEXT_REFRESH = datetime.min.replace(tzinfo=UTC)


def saved_forecast(path=PATH):
    """Saved output is always visibly saved, irrespective of retrieval age."""
    try:
        return PaletteForecast.model_validate_json(
            path.read_text(encoding="utf-8")
        ).model_copy(update={"availability": "stale"})
    except (OSError, ValueError):
        return PaletteForecast(days={}, availability="missing")


def fetch_forecast(now):
    """One city point and seven days; never transmit a user's journey."""
    params = {
        key: SETTINGS[key]
        for key in ("latitude", "longitude", "timezone", "forecast_days")
    }
    params["daily"] = "temperature_2m_mean"
    with httpx.Client(timeout=SETTINGS["timeout_seconds"]) as client:
        with client.stream("GET", SETTINGS["endpoint"], params=params) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > SETTINGS["max_response_bytes"]:
                    raise ValueError("Forecast response too large")
    payload = json.loads(content)
    if payload["daily_units"]["temperature_2m_mean"] != "°C":
        raise ValueError("Forecast unit mismatch")
    daily = payload["daily"]
    dates, values = daily["time"], daily["temperature_2m_mean"]
    if len(dates) != len(values) or len(dates) > SETTINGS["forecast_days"]:
        raise ValueError("Forecast day count mismatch")
    return PaletteForecast(
        days=dict(zip(dates, values, strict=True)),
        availability="current",
        provenance=Provenance(
            provider="Open-Meteo daily mean forecast · fixed Basel city point",
            source_url="https://open-meteo.com/en/docs",
            attribution="Weather data by Open-Meteo",
            licence="CC BY 4.0; free API noncommercial use only",
            fixture=False,
            retrieved_at=now,
        ),
    )


def palette_forecast(mode, path=PATH):
    """Offline reads only; hourly refresh with bounded retry and stale fallback."""
    global NEXT_REFRESH
    if mode == "offline":
        return saved_forecast(path)
    with LOCK:
        now = datetime.now(UTC)
        saved = saved_forecast(path)
        retrieved = saved.provenance.retrieved_at if saved.provenance else None
        if retrieved and timedelta(0) <= now - retrieved < timedelta(
            seconds=SETTINGS["refresh_seconds"]
        ):
            return saved.model_copy(update={"availability": "current"})
        if now < NEXT_REFRESH:
            return saved
        NEXT_REFRESH = now + timedelta(seconds=SETTINGS["retry_seconds"])
        try:
            result = fetch_forecast(now)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(result.model_dump_json(), encoding="utf-8")
            temporary.replace(path)
            NEXT_REFRESH = now + timedelta(seconds=SETTINGS["refresh_seconds"])
            return result
        except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError):
            return saved
