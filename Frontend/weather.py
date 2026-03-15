from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st
from Authentication import is_authenticated, login_screen

if not is_authenticated():
    login_screen(
        title="Sign in to view weather",
        description="Use Google or your local email/password account to continue.",
    )
    st.stop()

try:
    import pycountry
except Exception:
    pycountry = None

from openweatherapi import fetch_weather_bundle

LIVE_SUCCESS_NOTICE_SECONDS = 4.0


class MockWeatherRepository:
    """Provides placeholder weather records until API integration is wired."""

    def __init__(self) -> None:
        self.weather_descriptions = [
            "Clear",
            "Few clouds",
            "Scattered clouds",
            "Light rain",
            "Moderate rain",
            "Heavy rain",
            "Thunderstorm",
        ]

    def get_hourly_forecast(self, hours: int = 24) -> list[dict[str, Any]]:
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        rows: list[dict[str, Any]] = []
        day_biases = [0.0, 1.6, -1.1, 0.9, -0.5, 0.7, -0.8]

        for i in range(hours):
            timestamp = now + timedelta(hours=i)
            day_offset = (timestamp.date() - now.date()).days
            day_bias = day_biases[day_offset % len(day_biases)]
            base_temp = 18 + (5 if 11 <= timestamp.hour <= 16 else 0)
            temp = base_temp - abs(14 - timestamp.hour) * 0.55 + day_bias
            description = self._pick_description(timestamp.hour, i + day_offset)

            rows.append(
                {
                    "time": timestamp,
                    "temperature_c": round(temp, 1),
                    "humidity": max(25, min(95, 50 + (i * 2) % 40 + day_offset * 2)),
                    "wind_kmh": round(
                        max(2.0, 6 + (i * 1.2) % 16 + day_offset * 0.4), 1
                    ),
                    "description": description,
                }
            )

        return rows

    def _pick_description(self, hour: int, offset: int) -> str:
        if 13 <= hour <= 18:
            return self.weather_descriptions[3 + (offset % 3)]
        if 19 <= hour <= 22:
            return self.weather_descriptions[1 + (offset % 2)]
        if 4 <= hour <= 8:
            return self.weather_descriptions[0]
        return self.weather_descriptions[offset % 3]

    def get_location_label(self) -> str:
        return "Melbourne, AU"


class OpenWeatherRepository:
    """Loads weather forecast from OpenWeather for a configured city."""

    def __init__(
        self,
        fallback_repository: MockWeatherRepository,
        locality: str = "Melbourne",
        country: str = "AU",
    ) -> None:
        self.fallback_repository = fallback_repository
        self.locality = locality
        self.country = country
        self.used_fallback = False
        self.error_message = ""
        self.last_synced_at: datetime | None = None
        self.timezone_offset_seconds: int = 0
        self.raw_forecast_rows: list[dict[str, Any]] = []

    def get_hourly_forecast(self, hours: int = 24) -> list[dict[str, Any]]:
        self.used_fallback = False
        self.error_message = ""

        try:
            weather_bundle = fetch_weather_bundle(self.locality, self.country)
            payload = weather_bundle["forecast"]
            current_payload = weather_bundle["current"]
            self.timezone_offset_seconds = int(weather_bundle.get("timezone_offset", 0))
        except Exception as exc:
            self._set_fallback(f"OpenWeather request failed: {exc}")
            return self.fallback_repository.get_hourly_forecast(hours=hours)

        items = payload.get("list", [])
        if not items:
            self._set_fallback("OpenWeather response did not contain forecast items.")
            return self.fallback_repository.get_hourly_forecast(hours=hours)

        rows: list[dict[str, Any]] = []

        for item in items:
            dt_ts = item.get("dt")
            if not dt_ts:
                continue

            forecast_time = datetime.fromtimestamp(dt_ts, tz=timezone.utc).replace(
                tzinfo=None
            ) + timedelta(
                seconds=self.timezone_offset_seconds
            )

            main = item.get("main", {})
            wind = item.get("wind", {})
            weather_list = item.get("weather", [])
            description = (
                weather_list[0].get("description", "Unknown")
                if weather_list
                else "Unknown"
            )

            rows.append(
                {
                    "time": forecast_time,
                    "temperature_c": round(float(main.get("temp", 0.0)), 1),
                    "humidity": int(main.get("humidity", 0)),
                    "wind_kmh": round(float(wind.get("speed", 0.0)) * 3.6, 1),
                    "description": description.title(),
                }
            )

        current_row = self._build_current_row(current_payload)
        self.raw_forecast_rows = sorted(rows.copy(), key=lambda row: row["time"])
        known_points = rows.copy()
        if current_row is not None:
            known_points.append(current_row)

        if not known_points:
            self._set_fallback("No usable hourly rows were parsed from OpenWeather.")
            return self.fallback_repository.get_hourly_forecast(hours=hours)

        hourly_rows = self._build_hourly_rows(known_points=known_points, hours=hours)
        if not hourly_rows:
            self._set_fallback("Hourly interpolation failed for OpenWeather data.")
            return self.fallback_repository.get_hourly_forecast(hours=hours)

        self.last_synced_at = datetime.now()

        return hourly_rows

    def _build_hourly_rows(
        self, known_points: list[dict[str, Any]], hours: int
    ) -> list[dict[str, Any]]:
        known_points = sorted(known_points, key=lambda row: row["time"])
        start_time = (
            datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(seconds=self.timezone_offset_seconds)
        ).replace(minute=0, second=0, microsecond=0)
        hourly_rows: list[dict[str, Any]] = []

        for i in range(hours):
            target_time = start_time + timedelta(hours=i)
            before, after = self._find_bracketing_points(known_points, target_time)

            if before is None and after is None:
                continue
            if before is None:
                before = after
            if after is None:
                after = before

            assert before is not None and after is not None

            if before["time"] == after["time"]:
                ratio = 0.0
            else:
                total_seconds = (after["time"] - before["time"]).total_seconds()
                if total_seconds <= 0:
                    ratio = 0.0
                else:
                    ratio = (
                        target_time - before["time"]
                    ).total_seconds() / total_seconds
                    ratio = max(0.0, min(1.0, ratio))

            temperature = self._interpolate_numeric(
                before["temperature_c"], after["temperature_c"], ratio
            )
            humidity = int(
                round(
                    self._interpolate_numeric(
                        before["humidity"], after["humidity"], ratio
                    )
                )
            )
            wind_kmh = self._interpolate_numeric(
                before["wind_kmh"], after["wind_kmh"], ratio
            )
            description = before["description"] if ratio < 0.5 else after["description"]
            if i > 0 and description.startswith("Now - "):
                description = description.replace("Now - ", "", 1)

            hourly_rows.append(
                {
                    "time": target_time,
                    "temperature_c": round(temperature, 1),
                    "humidity": humidity,
                    "wind_kmh": round(wind_kmh, 1),
                    "description": description,
                }
            )

        return hourly_rows

    def _find_bracketing_points(
        self,
        known_points: list[dict[str, Any]],
        target_time: datetime,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        before: dict[str, Any] | None = None
        after: dict[str, Any] | None = None

        for point in known_points:
            point_time = point["time"]
            if point_time <= target_time:
                before = point
            if point_time >= target_time:
                after = point
                break

        return before, after

    def _interpolate_numeric(
        self, start_value: float, end_value: float, ratio: float
    ) -> float:
        return start_value + (end_value - start_value) * ratio

    def _build_current_row(
        self, current_payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        dt_ts = current_payload.get("dt")
        if not dt_ts:
            return None

        main = current_payload.get("main", {})
        wind = current_payload.get("wind", {})
        weather_list = current_payload.get("weather", [])
        description = (
            weather_list[0].get("description", "Unknown") if weather_list else "Unknown"
        )

        return {
            "time": datetime.fromtimestamp(dt_ts, tz=timezone.utc).replace(
                tzinfo=None
            )
            + timedelta(seconds=self.timezone_offset_seconds),
            "temperature_c": round(float(main.get("temp", 0.0)), 1),
            "humidity": int(main.get("humidity", 0)),
            "wind_kmh": round(float(wind.get("speed", 0.0)) * 3.6, 1),
            "description": f"Now - {description.title()}",
        }

    def get_location_label(self) -> str:
        if self.country:
            return f"{self.locality}, {self.country}"
        return str(self.locality)

    def _set_fallback(self, message: str) -> None:
        self.used_fallback = True
        self.error_message = message


class WeatherChartFactory:
    """Builds chart and table objects used by the Weather page."""

    @staticmethod
    def build_large_chart(hourly_rows: list[dict[str, Any]]) -> dict[str, Any]:
        chart_values = []
        for row in hourly_rows:
            chart_values.append(
                {
                    "time_label": row["time"].strftime("%H:%M"),
                    "temperature_c": row["temperature_c"],
                    "humidity": row["humidity"],
                    "wind_kmh": row["wind_kmh"],
                    "description": row["description"],
                }
            )

        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "height": 430,
            "data": {"values": chart_values},
            "params": [
                {
                    "name": "hover",
                    "select": {
                        "type": "point",
                        "fields": ["time_label"],
                        "nearest": True,
                        "on": "mousemove",
                        "clear": "mouseout",
                    },
                }
            ],
            "encoding": {
                "x": {
                    "field": "time_label",
                    "type": "ordinal",
                    "title": "Hour",
                    "sort": None,
                }
            },
            "layer": [
                {
                    "mark": {"type": "line", "strokeWidth": 4, "color": "#0284c7"},
                    "encoding": {
                        "y": {
                            "field": "temperature_c",
                            "type": "quantitative",
                            "title": "Temperature (°C)",
                        },
                        "tooltip": [
                            {"field": "time_label", "type": "nominal", "title": "Time"},
                            {
                                "field": "temperature_c",
                                "type": "quantitative",
                                "title": "Temperature (°C)",
                            },
                            {
                                "field": "description",
                                "type": "nominal",
                                "title": "Description",
                            },
                            {
                                "field": "humidity",
                                "type": "quantitative",
                                "title": "Humidity (%)",
                            },
                            {
                                "field": "wind_kmh",
                                "type": "quantitative",
                                "title": "Wind (km/h)",
                            },
                        ],
                    },
                },
                {
                    "transform": [{"filter": {"param": "hover", "empty": False}}],
                    "mark": {
                        "type": "rule",
                        "strokeDash": [6, 4],
                        "color": "#64748b",
                        "size": 2,
                    },
                    "encoding": {"x": {"field": "time_label", "type": "ordinal"}},
                },
                {
                    "mark": {"type": "circle", "size": 130, "opacity": 0.95},
                    "encoding": {
                        "y": {"field": "temperature_c", "type": "quantitative"},
                        "color": {
                            "field": "description",
                            "type": "nominal",
                            "title": "Condition",
                            "scale": {
                                "domain": [
                                    "Clear",
                                    "Few clouds",
                                    "Scattered clouds",
                                    "Light rain",
                                    "Moderate rain",
                                    "Heavy rain",
                                    "Thunderstorm",
                                ],
                                "range": [
                                    "#0ea5e9",
                                    "#60a5fa",
                                    "#93c5fd",
                                    "#4ade80",
                                    "#22c55e",
                                    "#16a34a",
                                    "#ef4444",
                                ],
                            },
                        },
                        "tooltip": [
                            {
                                "field": "description",
                                "type": "nominal",
                                "title": "Condition",
                            },
                            {"field": "time_label", "type": "nominal", "title": "Time"},
                        ],
                        "opacity": {
                            "condition": {"param": "hover", "value": 1},
                            "value": 0.85,
                        },
                    },
                },
            ],
            "config": {
                "axis": {"labelFontSize": 12, "titleFontSize": 13},
                "legend": {
                    "labelFontSize": 12,
                    "titleFontSize": 13,
                    "orient": "bottom",
                },
            },
        }

    @staticmethod
    def build_table_rows(hourly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        display_rows: list[dict[str, Any]] = []
        for row in hourly_rows:
            time_emoji = WeatherChartFactory._time_emoji(row["time"].hour)
            description_emoji = WeatherChartFactory._description_emoji(
                row["description"]
            )
            display_rows.append(
                {
                    "🕒 Time": f"{time_emoji} {row['time'].strftime('%a %H:%M')}",
                    "🌡️ Temp (°C)": row["temperature_c"],
                    "💧 Humidity (%)": row["humidity"],
                    "💨 Wind (km/h)": row["wind_kmh"],
                    "☁️ Description": f"{description_emoji} {row['description']}",
                }
            )
        return display_rows

    @staticmethod
    def _time_emoji(hour: int) -> str:
        # Daytime icon between 6AM and 5:59PM; moon icon otherwise.
        return "☀️" if 6 <= hour < 18 else "🌙"

    @staticmethod
    def _description_emoji(description: str) -> str:
        desc = description.lower()
        if "thunder" in desc:
            return "⛈️"
        if "rain" in desc or "drizzle" in desc:
            return "🌧️"
        if "snow" in desc:
            return "❄️"
        if "mist" in desc or "fog" in desc or "haze" in desc:
            return "🌫️"
        if "overcast" in desc:
            return "☁️"
        if "cloud" in desc:
            return "⛅"
        if "clear" in desc:
            return "☀️"
        return "🌤️"


class WeatherPage:
    """Coordinates weather data and UI rendering for the Streamlit page."""

    def __init__(self, weather_repository: Any) -> None:
        self.weather_repository = weather_repository

    def render(self) -> None:
        self._sync_location_from_saved_selection()
        all_hourly_rows = self._load_cached_or_fetch_rows(hours=72)
        raw_hourly_rows = st.session_state.get(
            "weather_cached_raw_rows", all_hourly_rows
        )
        next_24_rows = all_hourly_rows[:24]
        if "weather_chart_day_offset" not in st.session_state:
            st.session_state.weather_chart_day_offset = 0
        else:
            st.session_state.weather_chart_day_offset = min(
                1, max(0, int(st.session_state.weather_chart_day_offset))
            )

        location_label = "Melbourne, AU"
        if hasattr(self.weather_repository, "get_location_label"):
            location_label = self.weather_repository.get_location_label()

        self._render_styles()
        self._render_header(location_label)
        self._render_data_source_notice()
        self._render_metrics(next_24_rows)
        self._render_large_forecast_chart(
            all_hourly_rows, location_label, raw_hourly_rows
        )
        self._render_hourly_table(all_hourly_rows)

    def _sync_location_from_saved_selection(self) -> None:
        saved_city = str(st.session_state.get("saved_city", "")).strip()
        saved_country = str(st.session_state.get("saved_country", "")).strip()

        # Normalize placeholder values coming from UI summary fields.
        if saved_city.lower() in {"n/a", "na", "none", "null"}:
            saved_city = ""
        if saved_country.lower() in {"n/a", "na", "none", "null"}:
            saved_country = ""

        if saved_city:
            target_locality = saved_city
            target_country = (
                self._to_country_code(saved_country) if saved_country else ""
            )
        elif saved_country:
            # If city is missing, query by country/locality text instead of
            # mixing default Melbourne with a new country code.
            target_locality = saved_country
            target_country = ""
        else:
            target_locality = "Melbourne"
            target_country = "AU"

        # Compare against what was actually last fetched, not the freshly-constructed
        # repository defaults, so day-navigation reruns never bust the cache.
        cached_meta = st.session_state.get("weather_cached_meta", {})
        prev_locality = str(cached_meta.get("locality", "")).strip()
        prev_country = str(cached_meta.get("country", "")).strip().upper()

        if (
            prev_locality
            and target_locality == prev_locality
            and target_country == prev_country
        ):
            # Location unchanged - keep the existing cache and sync repo attrs.
            if hasattr(self.weather_repository, "locality"):
                self.weather_repository.locality = target_locality
            if hasattr(self.weather_repository, "country"):
                self.weather_repository.country = target_country
            return

        if hasattr(self.weather_repository, "locality"):
            self.weather_repository.locality = target_locality
        if hasattr(self.weather_repository, "country"):
            self.weather_repository.country = target_country

        # Location changed - invalidate cache so new data is fetched.
        st.session_state.pop("weather_cached_rows", None)
        st.session_state.pop("weather_cached_meta", None)
        st.session_state.pop("weather_cached_raw_rows", None)

    def _to_country_code(self, country_name_or_code: str) -> str:
        country = country_name_or_code.strip()
        if not country:
            return "AU"

        if len(country) == 2 and country.isalpha():
            return country.upper()

        if pycountry is not None:
            try:
                return str(pycountry.countries.lookup(country).alpha_2).upper()
            except LookupError:
                pass

        # Fallback: let OpenWeather geocoding attempt to resolve the provided country text.
        return country

    def _load_cached_or_fetch_rows(self, hours: int) -> list[dict[str, Any]]:
        cache_key = "weather_cached_rows"
        meta_key = "weather_cached_meta"

        if cache_key in st.session_state:
            cached_offset = st.session_state.get(meta_key, {}).get(
                "timezone_offset_seconds", 0
            )
            if hasattr(self.weather_repository, "timezone_offset_seconds"):
                self.weather_repository.timezone_offset_seconds = int(cached_offset)
            return st.session_state[cache_key]

        rows = self.weather_repository.get_hourly_forecast(hours=hours)
        raw_rows = list(getattr(self.weather_repository, "raw_forecast_rows", rows))
        st.session_state[cache_key] = rows
        st.session_state["weather_cached_raw_rows"] = raw_rows
        st.session_state[meta_key] = {
            "used_fallback": bool(
                getattr(self.weather_repository, "used_fallback", False)
            ),
            "error_message": str(getattr(self.weather_repository, "error_message", "")),
            "last_synced_at": getattr(self.weather_repository, "last_synced_at", None),
            "timezone_offset_seconds": int(
                getattr(self.weather_repository, "timezone_offset_seconds", 0)
            ),
            "locality": str(getattr(self.weather_repository, "locality", "")),
            "country": str(getattr(self.weather_repository, "country", "")).upper(),
        }
        return rows

    def _location_now(self) -> datetime:
        offset = timedelta(
            seconds=int(getattr(self.weather_repository, "timezone_offset_seconds", 0))
        )
        return datetime.now(timezone.utc).replace(tzinfo=None) + offset

    def _render_styles(self) -> None:
        st.html(
            """
            <style>
            /* Slide-fade-DOWN keyframe */
            @keyframes slideFadeDown {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            /* Apply to all buttons */
            div[data-testid="stButton"] button {
                animation: slideFadeDown 0.4s ease forwards;
                transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.28s cubic-bezier(0.22, 1, 0.36, 1), filter 0.28s cubic-bezier(0.22, 1, 0.36, 1);
            }

            /* Apply to bordered column/grid boxes */
            div[data-testid="stColumn"] {
                animation: slideFadeDown 0.4s ease forwards;
            }

            /* Apply to horizontal divider */
            div[data-testid="stDivider"] {
                animation: slideFadeDown 0.4s ease 0.3s forwards;
                opacity: 0;
            }

            /* Apply to alerts (success/warning/info/error) */
            div[data-testid="stAlert"] {
                animation: slideFadeDown 0.4s ease forwards;
            }

            /* Stagger for buttons */
            div[data-testid="stButton"]:nth-child(1) button { animation-delay: 0.0s; }
            div[data-testid="stButton"]:nth-child(2) button { animation-delay: 0.1s; }
            div[data-testid="stButton"]:nth-child(3) button { animation-delay: 0.2s; }
            div[data-testid="stButton"]:nth-child(4) button { animation-delay: 0.3s; }

            /* Stagger for grid boxes */
            div[data-testid="stColumn"]:nth-child(1) { animation-delay: 0.0s; }
            div[data-testid="stColumn"]:nth-child(2) { animation-delay: 0.1s; }
            div[data-testid="stColumn"]:nth-child(3) { animation-delay: 0.2s; }
            div[data-testid="stColumn"]:nth-child(4) { animation-delay: 0.3s; }

            /* Keep hover effect on buttons */
            div[data-testid="stButton"] button:hover {
                transform: translateY(-2px) scale(1.02);
                box-shadow: 0 8px 18px rgba(0, 0, 0, 0.2);
            }

            /* Dedicated animation for weather refresh icon button */
            @keyframes refreshButtonFloat {
                0%,
                100% {
                    transform: translateY(0);
                }
                50% {
                    transform: translateY(-5px);
                }
            }

            @keyframes refreshButtonWiggle {
                0% {
                    transform: translateX(-2px) scale(1.05) rotate(0deg);
                }
                25% {
                    transform: translateX(-4px) scale(1.06) rotate(-1deg);
                }
                50% {
                    transform: translateX(-2px) scale(1.07) rotate(1deg);
                }
                75% {
                    transform: translateX(-4px) scale(1.06) rotate(-1deg);
                }
                100% {
                    transform: translateX(-2px) scale(1.05) rotate(0deg);
                }
            }

            .st-key-refresh_weather_button button {
                animation: refreshButtonFloat 2.2s ease-in-out infinite;
                border: 1px solid rgba(59, 130, 246, 0.35);
                transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1), filter 0.25s cubic-bezier(0.22, 1, 0.36, 1);
            }

            .st-key-refresh_weather_button button:hover {
                animation: refreshButtonWiggle 0.9s ease-in-out infinite;
                box-shadow: 0 10px 22px rgba(59, 130, 246, 0.45);
                filter: brightness(1.08) saturate(1.12);
            }

            /* Weather page visual shell styling */
            .weather-shell {
                padding: 1.2rem;
                border-radius: 16px;
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 45%, #e0f2fe 100%);
                border: 1px solid #bfdbfe;
                margin-bottom: 1rem;
                animation: slideFadeDown 0.5s ease forwards;
            }
            .weather-title {
                font-size: 2rem;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 0.3rem;
            }
            .weather-subtitle {
                color: #334155;
                font-size: 1rem;
            }

            /* Prevent the 3-dot element toolbar from covering chart points near top-right */
            div[data-testid="stVegaLiteChart"] div[data-testid="stElementToolbar"] {
                display: none !important;
            }

            @keyframes liveSuccessFadeAway {
                0% {
                    opacity: 0;
                    transform: translateY(-6px);
                    max-height: 48px;
                    margin-top: 0.35rem;
                    padding-top: 0.55rem;
                    padding-bottom: 0.55rem;
                    border-width: 1px;
                }
                12% {
                    opacity: 1;
                    transform: translateY(0);
                    max-height: 48px;
                    margin-top: 0.35rem;
                    padding-top: 0.55rem;
                    padding-bottom: 0.55rem;
                    border-width: 1px;
                }
                78% {
                    opacity: 1;
                    transform: translateY(0);
                    max-height: 48px;
                    margin-top: 0.35rem;
                    padding-top: 0.55rem;
                    padding-bottom: 0.55rem;
                    border-width: 1px;
                }
                100% {
                    opacity: 0;
                    transform: translateY(-4px);
                    max-height: 0;
                    margin-top: 0;
                    padding-top: 0;
                    padding-bottom: 0;
                    border-width: 0;
                }
            }

            .live-success-pill {
                display: block;
                width: fit-content;
                overflow: hidden;
                margin: 0.35rem 0 0;
                padding: 0.55rem 0.9rem;
                border-radius: 0.6rem;
                font-size: 0.92rem;
                font-weight: 600;
                color: #065f46;
                background: #d1fae5;
                border: 1px solid #86efac;
                animation: liveSuccessFadeAway 3.8s ease forwards;
            }
            </style>
            """
        )

    def _render_header(self, location_label: str) -> None:
        st.markdown(
            f"""
            <div class="weather-shell">
                <div class="weather-title">🌤️ Weather Overview</div>
                <div class="weather-subtitle">📍 {location_label} | 🕒 Updated {datetime.now().strftime("%d %b %Y, %H:%M")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _render_data_source_notice(self) -> None:
        meta = st.session_state.get("weather_cached_meta", {})
        used_fallback = bool(meta.get("used_fallback", False))
        error_message = str(meta.get("error_message", "Unknown error"))
        last_synced_at = meta.get("last_synced_at")
        error_text = error_message.lower()

        if used_fallback:
            if "could not find location" in error_text:
                st.warning(
                    "We couldn't find that location. Please check the city/country and try again."
                )
            elif "request failed" in error_text or "timeout" in error_text:
                st.warning(
                    "Weather service is temporarily unavailable. Showing backup weather data for now."
                )
            else:
                st.warning(
                    "Live weather is unavailable right now. Showing backup weather data."
                )

            if error_message:
                st.caption(f"Technical details: {error_message}")
        else:
            show_live_success = False
            if isinstance(last_synced_at, datetime):
                elapsed = (datetime.now() - last_synced_at).total_seconds()
                show_live_success = elapsed < LIVE_SUCCESS_NOTICE_SECONDS
            elif last_synced_at:
                # Fallback for unexpected timestamp formats from session state.
                show_live_success = True

            if show_live_success:
                st.markdown(
                    "<div class='live-success-pill'>Live OpenWeather data loaded.</div>",
                    unsafe_allow_html=True,
                )

        sync_text = "Last synced: Not synced yet"
        if last_synced_at:
            sync_text = f"Last synced: {last_synced_at.strftime('%d %b %Y %H:%M:%S')}"

        sync_col, refresh_col = st.columns([8, 1], vertical_alignment="center")
        with sync_col:
            st.caption(sync_text)
        with refresh_col:
            refresh_clicked = st.button(
                "🔄",
                key="refresh_weather_button",
                use_container_width=False,
                help="Refresh live weather",
                type="primary",
            )

        if refresh_clicked:
            st.session_state.pop("weather_cached_rows", None)
            st.session_state.pop("weather_cached_meta", None)
            st.session_state.pop("weather_cached_raw_rows", None)
            st.rerun()

    def _render_metrics(self, hourly_rows: list[dict[str, Any]]) -> None:
        current_temp = float(hourly_rows[0]["temperature_c"])
        avg_humidity = int(
            sum(row["humidity"] for row in hourly_rows) / len(hourly_rows)
        )
        max_wind = float(max(row["wind_kmh"] for row in hourly_rows))

        m1, m2, m3 = st.columns(3)
        m1.metric("🌡️ Current Temp", f"{current_temp:.1f} °C")
        m2.metric("💧 Average Humidity", f"{avg_humidity}%")
        m3.metric("💨 Peak Wind", f"{max_wind:.1f} km/h")

    def _render_large_forecast_chart(
        self,
        hourly_rows: list[dict[str, Any]],
        location_label: str,
        raw_hourly_rows: list[dict[str, Any]],
    ) -> None:
        st.markdown("### 📈 Forecast Chart")
        st.caption(
            "🌡️ Today shows the next 12 hours. Tomorrow shows full day forecast. The red dot marks the current hour."
        )
        st.markdown(
            f"""
            <div style=\"text-align: center; font-weight: 600; color: #334155; margin-bottom: 0.5rem;\">
                📍 {location_label}
            </div>
            """,
            unsafe_allow_html=True,
        )

        today = self._location_now().date()
        selected_offset = int(st.session_state.get("weather_chart_day_offset", 0))

        c_prev, c_label, c_next = st.columns([1, 2, 1])
        with c_prev:
            if selected_offset > 0:
                if st.button(
                    " **Previous Day**",
                    key="chart_prev_day",
                    use_container_width=True,
                    type="primary",
                    icon="⬅️",
                ):
                    current = int(st.session_state.get("weather_chart_day_offset", 0))
                    st.session_state.weather_chart_day_offset = max(0, current - 1)
                    st.rerun()

            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)
        with c_label:
            selected_offset = int(st.session_state.get("weather_chart_day_offset", 0))
            selected_date = today + timedelta(days=selected_offset)
            day_title = ["Today", "Tomorrow"][selected_offset]
            st.markdown(
                f'<div style="text-align:center; font-weight:700; margin-top:0.3rem;">{day_title} ({selected_date.strftime("%d %b")})</div>',
                unsafe_allow_html=True,
            )
        with c_next:
            if selected_offset < 1:
                if st.button(
                    "**Next Day**",
                    key="chart_next_day",
                    use_container_width=True,
                    icon="➡️",
                    type="primary",
                ):
                    current = int(st.session_state.get("weather_chart_day_offset", 0))
                    st.session_state.weather_chart_day_offset = min(1, current + 1)
                    st.rerun()

            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)

        selected_offset = int(st.session_state.get("weather_chart_day_offset", 0))
        selected_date = today + timedelta(days=selected_offset)

        day_rows = [row for row in hourly_rows if row["time"].date() == selected_date]
        raw_day_rows = [
            row for row in raw_hourly_rows if row["time"].date() == selected_date
        ]
        if selected_offset != 0:
            day_rows = raw_day_rows

        if not day_rows and selected_offset != 0:
            st.info("No hourly forecast available for this day.")
            return

        now_local = self._location_now()
        now_anchor = now_local.replace(minute=0, second=0, microsecond=0)
        current_hour = int(now_local.hour)
        current_date = now_local.date()

        if selected_offset == 0:
            next_12_rows = [row for row in hourly_rows if row["time"] >= now_anchor]
            next_12_rows = sorted(next_12_rows, key=lambda row: row["time"])[:12]

            if not next_12_rows:
                st.info("No hourly forecast available for the next 12 hours.")
                return

            chart_values = [
                {
                    "time_iso": row["time"].strftime("%Y-%m-%dT%H:%M:%S"),
                    "time_label": row["time"].strftime("%H:%M"),
                    "temperature_c": row["temperature_c"],
                    "is_current_hour": row["time"].hour == current_hour
                    and row["time"].date() == current_date,
                }
                for row in next_12_rows
            ]
        else:
            chart_values = [
                {
                    "time_iso": row["time"].strftime("%Y-%m-%dT%H:%M:%S"),
                    "time_label": row["time"].strftime("%H:%M"),
                    "temperature_c": row["temperature_c"],
                    "is_current_hour": False,
                }
                for row in day_rows
            ]

        temp_source_rows = raw_hourly_rows if raw_hourly_rows else hourly_rows
        temp_values = [
            float(row["temperature_c"])
            for row in temp_source_rows
            if "temperature_c" in row
        ]
        if temp_values:
            y_min = round(min(temp_values) - 1.0, 1)
            y_max = round(max(temp_values) + 1.0, 1)
        else:
            y_min, y_max = 0.0, 40.0

        chart_spec = {
            "data": {"values": chart_values},
            "layer": [
                {
                    "mark": {"type": "line", "strokeWidth": 3, "color": "#0284c7"},
                    "encoding": {
                        "x": {
                            "field": "time_iso",
                            "type": "temporal",
                            "title": "Hour",
                            "axis": {"format": "%H:%M"},
                        },
                        "y": {
                            "field": "temperature_c",
                            "type": "quantitative",
                            "title": "Temperature (°C)",
                            "scale": {"domain": [y_min, y_max], "nice": False},
                        },
                        "tooltip": [
                            {"field": "time_label", "type": "nominal", "title": "Time"},
                            {
                                "field": "temperature_c",
                                "type": "quantitative",
                                "title": "Temperature (°C)",
                                "format": ".1f",
                            },
                        ],
                    },
                },
                {
                    "mark": {
                        "type": "point",
                        "filled": True,
                        "size": 42,
                        "color": "#0284c7",
                    },
                    "transform": [{"filter": "datum.temperature_c != null"}],
                    "encoding": {
                        "x": {
                            "field": "time_iso",
                            "type": "temporal",
                        },
                        "y": {"field": "temperature_c", "type": "quantitative"},
                        "tooltip": [
                            {"field": "time_label", "type": "nominal", "title": "Time"},
                            {
                                "field": "temperature_c",
                                "type": "quantitative",
                                "title": "Temperature (°C)",
                                "format": ".1f",
                            },
                        ],
                    },
                },
                {
                    "mark": {
                        "type": "point",
                        "filled": True,
                        "size": 120,
                        "color": "#dc2626",
                    },
                    "transform": [
                        {"filter": "datum.temperature_c != null"},
                        {"filter": "datum.is_current_hour == true"},
                    ],
                    "encoding": {
                        "x": {
                            "field": "time_iso",
                            "type": "temporal",
                        },
                        "y": {"field": "temperature_c", "type": "quantitative"},
                        "tooltip": [
                            {"field": "time_label", "type": "nominal", "title": "Time"},
                            {
                                "field": "temperature_c",
                                "type": "quantitative",
                                "title": "Temperature (°C)",
                                "format": ".1f",
                            },
                        ],
                    },
                },
            ],
        }

        st.vega_lite_chart(
            chart_spec,
            use_container_width=True,
            key=f"forecast_chart_{selected_date.isoformat()}_{selected_offset}",
        )

    def _render_hourly_table(self, hourly_rows: list[dict[str, Any]]) -> None:
        st.markdown("### 🕒 Hourly Details")

        today = self._location_now().date()
        tomorrow = today + timedelta(days=1)
        today_rows = [row for row in hourly_rows if row["time"].date() == today]

        tomorrow_rows = [row for row in hourly_rows if row["time"].date() == tomorrow]

        tab_next, tab_tomorrow = st.tabs(["Today", "Tomorrow"])

        with tab_next:
            if today_rows:
                display_rows = WeatherChartFactory.build_table_rows(today_rows)
                st.table(display_rows)
            else:
                st.info("No hourly forecast available for today yet.")

        with tab_tomorrow:
            if tomorrow_rows:
                display_rows = WeatherChartFactory.build_table_rows(tomorrow_rows)
                st.table(display_rows)
            else:
                st.info("No hourly forecast available for tomorrow yet.")


fallback_repository = MockWeatherRepository()
weather_repository = OpenWeatherRepository(
    fallback_repository=fallback_repository,
    locality="Melbourne",
    country="AU",
)

weather_page = WeatherPage(weather_repository=weather_repository)
weather_page.render()
