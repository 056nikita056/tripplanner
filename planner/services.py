from __future__ import annotations

from dataclasses import dataclass

import requests
from django.core.cache import cache


@dataclass
class WeatherResult:
    ok: bool
    summary: str
    data: dict


def get_forecast(latitude: float, longitude: float) -> WeatherResult:
    if latitude is None or longitude is None:
        return WeatherResult(ok=False, summary='No coordinates for destination.', data={})

    cache_key = f"wx:{latitude}:{longitude}"
    cached = cache.get(cache_key)
    if cached:
        return WeatherResult(ok=True, summary='Forecast loaded from cache.', data=cached)

    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'current': 'temperature_2m,wind_speed_10m',
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
        'timezone': 'auto',
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return WeatherResult(ok=False, summary='Weather service is temporarily unavailable.', data={})

    cache.set(cache_key, data, 60 * 20)
    return WeatherResult(ok=True, summary='Forecast loaded from Open-Meteo.', data=data)
