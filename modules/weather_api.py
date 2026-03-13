"""
weather_api.py – Fetching real-time Melbourne weather via OpenWeatherMap.

Environment variables (stored in .env)
---------------------------------------
OPENWEATHER_API_KEY – your OpenWeatherMap API key.

TODO (team): Ensure the .env file is populated before running the app.
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
_CITY = "Melbourne,AU"
_UNITS = "metric"  # Celsius


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_melbourne_weather() -> dict:
    """
    Fetch the current weather for Melbourne from OpenWeatherMap.

    Returns a dict with at least::

        {
            "temperature": float,   # °C
            "description": str,     # e.g. "light rain"
            "humidity": int,        # %
            "wind_speed": float,    # m/s
            "icon": str,            # OWM icon code, e.g. "10d"
        }

    Raises
    ------
    EnvironmentError
        If ``OPENWEATHER_API_KEY`` is not set.
    requests.HTTPError
        If the API call fails.

    TODO (team): Optionally extend to include a 5-day forecast using
    the /forecast endpoint.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        # Return mock data so the UI works during development without a key.
        return _mock_weather()

    params = {
        "q": _CITY,
        "appid": api_key,
        "units": _UNITS,
    }
    response = requests.get(_BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return {
        "temperature": data.get("main", {}).get("temp", 0.0),
        "description": data.get("weather", [{}])[0].get("description", "").capitalize(),
        "humidity": data.get("main", {}).get("humidity", 0),
        "wind_speed": data.get("wind", {}).get("speed", 0.0),
        "icon": data.get("weather", [{}])[0].get("icon", ""),
    }


def _mock_weather() -> dict:
    """Return placeholder weather data when no API key is configured."""
    return {
        "temperature": 18.0,
        "description": "Partly cloudy (mock)",
        "humidity": 65,
        "wind_speed": 3.5,
        "icon": "02d",
    }


def weather_to_tags(weather: dict) -> list[str]:
    """
    Convert a weather dict into a list of clothing-relevant tags.

    Examples: ["warm", "sunny"], ["cold", "rainy", "windy"]

    TODO (team): Refine thresholds to suit Melbourne's climate.
    """
    tags: list[str] = []

    temp = weather.get("temperature", 20)
    if temp >= 25:
        tags.append("warm")
    elif temp >= 15:
        tags.append("mild")
    else:
        tags.append("cold")

    desc = weather.get("description", "").lower()
    if "rain" in desc or "drizzle" in desc:
        tags.append("rainy")
    if "snow" in desc:
        tags.append("snowy")
    if "sun" in desc or "clear" in desc:
        tags.append("sunny")
    if "wind" in desc or weather.get("wind_speed", 0) > 7:
        tags.append("windy")

    return tags
