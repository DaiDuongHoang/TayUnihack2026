from datetime import datetime, timedelta
import os
from typing import Any

import requests
import streamlit as st


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

        for i in range(hours):
            timestamp = now + timedelta(hours=i)
            base_temp = 18 + (5 if 11 <= timestamp.hour <= 16 else 0)
            temp = base_temp - abs(14 - timestamp.hour) * 0.55
            description = self._pick_description(timestamp.hour, i)

            rows.append(
                {
                    "time": timestamp,
                    "temperature_c": round(temp, 1),
                    "humidity": 50 + (i * 2) % 40,
                    "wind_kmh": round(6 + (i * 1.2) % 16, 1),
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
        api_key: str | None,
        fallback_repository: MockWeatherRepository,
        city_query: str = "Melbourne,AU",
    ) -> None:
        self.api_key = api_key
        self.city_query = city_query
        self.fallback_repository = fallback_repository
        self.used_fallback = False
        self.error_message = ""
        self.last_synced_at: datetime | None = None

    def get_hourly_forecast(self, hours: int = 24) -> list[dict[str, Any]]:
        self.used_fallback = False
        self.error_message = ""

        if not self.api_key:
            self._set_fallback("OPENWEATHER_API_KEY is missing.")
            return self.fallback_repository.get_hourly_forecast(hours=hours)

        url = "https://api.openweathermap.org/data/2.5/forecast"
        current_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": self.city_query,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            response = requests.get(url, params=params, timeout=12)
            response.raise_for_status()
            payload = response.json()
            current_response = requests.get(current_url, params=params, timeout=12)
            current_response.raise_for_status()
            current_payload = current_response.json()
        except requests.RequestException as exc:
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

            forecast_time = datetime.fromtimestamp(dt_ts)

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
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0)
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
            "time": datetime.fromtimestamp(dt_ts),
            "temperature_c": round(float(main.get("temp", 0.0)), 1),
            "humidity": int(main.get("humidity", 0)),
            "wind_kmh": round(float(wind.get("speed", 0.0)) * 3.6, 1),
            "description": f"Now - {description.title()}",
        }

    def get_location_label(self) -> str:
        city_name = self.city_query.replace(",", ", ")
        return city_name

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
                            "title": "Temperature (C)",
                        },
                        "tooltip": [
                            {"field": "time_label", "type": "nominal", "title": "Time"},
                            {
                                "field": "temperature_c",
                                "type": "quantitative",
                                "title": "Temperature (C)",
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
            display_rows.append(
                {
                    "🕒 Time": row["time"].strftime("%a %H:%M"),
                    "🌡️ Temp (C)": row["temperature_c"],
                    "💧 Humidity (%)": row["humidity"],
                    "💨 Wind (km/h)": row["wind_kmh"],
                    "☁️ Description": row["description"],
                }
            )
        return display_rows


class WeatherPage:
    """Coordinates weather data and UI rendering for the Streamlit page."""

    def __init__(self, weather_repository: Any) -> None:
        self.weather_repository = weather_repository

    def render(self) -> None:
        hourly_rows = self.weather_repository.get_hourly_forecast()

        location_label = "Melbourne, AU"
        if hasattr(self.weather_repository, "get_location_label"):
            location_label = self.weather_repository.get_location_label()

        self._render_styles()
        self._render_header(location_label)
        self._render_data_source_notice()
        self._render_metrics(hourly_rows)
        self._render_large_forecast_chart(hourly_rows)
        self._render_hourly_table(hourly_rows)

    def _render_styles(self) -> None:
        st.markdown(
            """
			<style>
				.weather-shell {
					padding: 1.2rem;
					border-radius: 16px;
					background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 45%, #e0f2fe 100%);
					border: 1px solid #bfdbfe;
					margin-bottom: 1rem;
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
			</style>
			""",
            unsafe_allow_html=True,
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
        if (
            hasattr(self.weather_repository, "used_fallback")
            and self.weather_repository.used_fallback
        ):
            st.warning(
                "OpenWeather unavailable, showing mock data. "
                f"Details: {getattr(self.weather_repository, 'error_message', 'Unknown error')}"
            )
        else:
            st.success("Live OpenWeather data loaded for Melbourne.")

        if hasattr(self.weather_repository, "last_synced_at"):
            last_synced_at = getattr(self.weather_repository, "last_synced_at")
            if last_synced_at:
                st.caption(
                    f"Last synced: {last_synced_at.strftime('%d %b %Y %H:%M:%S')}"
                )

        if st.button("Refresh live weather", use_container_width=False):
            st.rerun()

    def _render_metrics(self, hourly_rows: list[dict[str, Any]]) -> None:
        current_temp = float(hourly_rows[0]["temperature_c"])
        avg_humidity = int(
            sum(row["humidity"] for row in hourly_rows) / len(hourly_rows)
        )
        max_wind = float(max(row["wind_kmh"] for row in hourly_rows))
        unique_conditions = len({row["description"] for row in hourly_rows})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Current Temp", f"{current_temp:.1f} C")
        m2.metric("💧 Avg Humidity", f"{avg_humidity}%")
        m3.metric("💨 Peak Wind", f"{max_wind:.1f} km/h")
        m4.metric("☁️ Condition Types", f"{unique_conditions}")

    def _render_large_forecast_chart(self, hourly_rows: list[dict[str, Any]]) -> None:
        st.markdown("### 📈 Next 24 Hours")
        st.caption(
            "🌡️ Live temperature trend for the next 24 hours (hourly points from current hour)."
        )

        chart_data = {
            "Time": [row["time"].strftime("%H:%M") for row in hourly_rows],
            "Temperature (C)": [row["temperature_c"] for row in hourly_rows],
        }
        st.line_chart(
            chart_data, x="Time", y="Temperature (C)", use_container_width=True
        )

    def _render_hourly_table(self, hourly_rows: list[dict[str, Any]]) -> None:
        st.markdown("### 🗂️ Hourly Details")
        display_rows = WeatherChartFactory.build_table_rows(hourly_rows)
        st.dataframe(display_rows, use_container_width=True, hide_index=True)


def resolve_openweather_api_key() -> str | None:
    try:
        key_from_secrets = st.secrets.get("OPENWEATHER_API_KEY")
        if key_from_secrets:
            return str(key_from_secrets)
    except Exception:
        pass

    key_from_env = os.getenv("OPENWEATHER_API_KEY")
    if key_from_env:
        return key_from_env

    return None


fallback_repository = MockWeatherRepository()
weather_repository = OpenWeatherRepository(
    api_key=resolve_openweather_api_key(),
    fallback_repository=fallback_repository,
    city_query="Melbourne,AU",
)

weather_page = WeatherPage(weather_repository=weather_repository)
weather_page.render()
