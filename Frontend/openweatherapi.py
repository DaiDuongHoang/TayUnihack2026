from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import requests
import streamlit as st


GEOCODE_URL = 'http://api.openweathermap.org/geo/1.0/direct'
CURRENT_WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather'
FORECAST_URL = 'https://api.openweathermap.org/data/2.5/forecast'


def get_api_key() -> str:
    apiKey = st.secrets.get('OPENWEATHER_API_KEY', '')
    if not apiKey:
        api_section = st.secrets.get('api', {})
        if isinstance(api_section, Mapping):
            apiKey = api_section.get('OPENWEATHER_API_KEY', '')

    if not apiKey:
        apiKey = os.getenv('OPENWEATHER_API_KEY', '')

    if apiKey.startswith('your_'):
        apiKey = ''

    if not apiKey:
        raise ValueError('OpenWeather API key is not configured')
    return apiKey


def build_location_query(locality: str, country: str = '') -> str:
    locality = locality.strip()
    country = country.strip()

    if not locality:
        raise ValueError('Location is required')

    return f'{locality},{country}' if country else locality


def get_coordinates(locality: str, country: str = '') -> dict:
    location_query = build_location_query(locality, country)
    response = requests.get(
        GEOCODE_URL,
        params={'q': location_query, 'appid': get_api_key(), 'limit': 1},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        raise ValueError(f'Could not find location: {location_query}')

    match = data[0]
    resolved_name = ', '.join(
        part
        for part in [match.get('name'), match.get('state'), match.get('country')]
        if part
    )

    return {
        'lat': match['lat'],
        'lon': match['lon'],
        'location_name': resolved_name or location_query,
    }


def fetch_current_weather(locality: str, country: str = '') -> dict:
    coordinates = get_coordinates(locality, country)
    response = requests.get(
        CURRENT_WEATHER_URL,
        params={
            'lat': coordinates['lat'],
            'lon': coordinates['lon'],
            'appid': get_api_key(),
            'units': 'metric',
        },
        timeout=15,
    )
    response.raise_for_status()
    weather = response.json()
    weather['resolved_location_name'] = coordinates['location_name']
    return weather


def fetch_forecast(locality: str, country: str = '') -> dict:
    coordinates = get_coordinates(locality, country)
    response = requests.get(
        FORECAST_URL,
        params={
            'lat': coordinates['lat'],
            'lon': coordinates['lon'],
            'appid': get_api_key(),
            'units': 'metric',
        },
        timeout=15,
    )
    response.raise_for_status()
    forecast = response.json()
    forecast['resolved_location_name'] = coordinates['location_name']
    return forecast


def fetch_weather_bundle(locality: str, country: str = '') -> dict[str, Any]:
    current_weather = fetch_current_weather(locality, country)
    forecast = fetch_forecast(locality, country)
    return {
        'location': current_weather.get(
            'resolved_location_name',
            forecast.get(
                'resolved_location_name', build_location_query(locality, country)
            ),
        ),
        'current': current_weather,
        'forecast': forecast,
        'timezone_offset': int(current_weather.get('timezone', 0)),
    }
