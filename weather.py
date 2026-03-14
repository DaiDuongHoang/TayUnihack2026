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

	def get_hourly_forecast(self, hours: int = 24) -> list[dict[str, Any]]:
		self.used_fallback = False
		self.error_message = ""

		if not self.api_key:
			self._set_fallback("OPENWEATHER_API_KEY is missing.")
			return self.fallback_repository.get_hourly_forecast(hours=hours)

		url = "https://api.openweathermap.org/data/2.5/forecast"
		params = {
			"q": self.city_query,
			"appid": self.api_key,
			"units": "metric",
		}

		try:
			response = requests.get(url, params=params, timeout=12)
			response.raise_for_status()
			payload = response.json()
		except requests.RequestException as exc:
			self._set_fallback(f"OpenWeather request failed: {exc}")
			return self.fallback_repository.get_hourly_forecast(hours=hours)

		items = payload.get("list", [])
		if not items:
			self._set_fallback("OpenWeather response did not contain forecast items.")
			return self.fallback_repository.get_hourly_forecast(hours=hours)

		rows: list[dict[str, Any]] = []
		first_time = datetime.fromtimestamp(items[0].get("dt", 0))
		end_time = first_time + timedelta(hours=hours)

		for item in items:
			dt_ts = item.get("dt")
			if not dt_ts:
				continue

			forecast_time = datetime.fromtimestamp(dt_ts)
			if forecast_time > end_time:
				break

			main = item.get("main", {})
			wind = item.get("wind", {})
			weather_list = item.get("weather", [])
			description = weather_list[0].get("description", "Unknown") if weather_list else "Unknown"

			rows.append(
				{
					"time": forecast_time,
					"temperature_c": round(float(main.get("temp", 0.0)), 1),
					"humidity": int(main.get("humidity", 0)),
					"wind_kmh": round(float(wind.get("speed", 0.0)) * 3.6, 1),
					"description": description.title(),
				}
			)

		if not rows:
			self._set_fallback("No usable hourly rows were parsed from OpenWeather.")
			return self.fallback_repository.get_hourly_forecast(hours=hours)

		return rows

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
				"x": {"field": "time_label", "type": "ordinal", "title": "Hour", "sort": None}
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
							{"field": "temperature_c", "type": "quantitative", "title": "Temperature (C)"},
							{"field": "description", "type": "nominal", "title": "Description"},
							{"field": "humidity", "type": "quantitative", "title": "Humidity (%)"},
							{"field": "wind_kmh", "type": "quantitative", "title": "Wind (km/h)"},
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
					"encoding": {
						"x": {"field": "time_label", "type": "ordinal"}
					},
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
							{"field": "description", "type": "nominal", "title": "Condition"},
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
				"legend": {"labelFontSize": 12, "titleFontSize": 13, "orient": "bottom"},
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
		self._render_integration_notes()

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
				<div class="weather-subtitle">📍 {location_label} | 🕒 Updated {datetime.now().strftime('%d %b %Y, %H:%M')}</div>
			</div>
			""",
			unsafe_allow_html=True,
		)

	def _render_data_source_notice(self) -> None:
		if hasattr(self.weather_repository, "used_fallback") and self.weather_repository.used_fallback:
			st.warning(
				"OpenWeather unavailable, showing mock data. "
				f"Details: {getattr(self.weather_repository, 'error_message', 'Unknown error')}"
			)
		else:
			st.success("Live OpenWeather data loaded for Melbourne.")

	def _render_metrics(self, hourly_rows: list[dict[str, Any]]) -> None:
		current_temp = float(hourly_rows[0]["temperature_c"])
		avg_humidity = int(sum(row["humidity"] for row in hourly_rows) / len(hourly_rows))
		max_wind = float(max(row["wind_kmh"] for row in hourly_rows))
		unique_conditions = len({row["description"] for row in hourly_rows})

		m1, m2, m3, m4 = st.columns(4)
		m1.metric("🌡️ Current Temp", f"{current_temp:.1f} C")
		m2.metric("💧 Avg Humidity", f"{avg_humidity}%")
		m3.metric("💨 Peak Wind", f"{max_wind:.1f} km/h")
		m4.metric("☁️ Condition Types", f"{unique_conditions}")

	def _render_large_forecast_chart(self, hourly_rows: list[dict[str, Any]]) -> None:
		st.markdown("### 📈 Next 24 Hours")
		st.caption("🌡️ Temperature trend for the next 24 hours.")

		chart_data = {
			"Time": [row["time"].strftime("%H:%M") for row in hourly_rows],
			"Temperature (C)": [row["temperature_c"] for row in hourly_rows],
		}
		st.line_chart(chart_data, x="Time", y="Temperature (C)", use_container_width=True)

	def _render_hourly_table(self, hourly_rows: list[dict[str, Any]]) -> None:
		st.markdown("### 🗂️ Hourly Details")
		display_rows = WeatherChartFactory.build_table_rows(hourly_rows)
		st.dataframe(display_rows, use_container_width=True, hide_index=True)

	def _render_integration_notes(self) -> None:
		with st.expander("🛠️ Notes for API Integration", expanded=False):
			st.write("🔑 Configure OPENWEATHER_API_KEY in Streamlit secrets or environment variables.")
			st.write("📍 Current default city is fixed to Melbourne,AU in OpenWeatherRepository.")
			st.write("📦 Keep fields: time, temperature_c, humidity, wind_kmh, description.")


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