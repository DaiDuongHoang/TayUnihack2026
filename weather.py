from datetime import datetime, timedelta
from typing import Any

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

	def __init__(self, weather_repository: MockWeatherRepository) -> None:
		self.weather_repository = weather_repository

	def render(self) -> None:
		hourly_rows = self.weather_repository.get_hourly_forecast()

		self._render_styles()
		self._render_header()
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

	def _render_header(self) -> None:
		st.markdown(
			f"""
			<div class="weather-shell">
				<div class="weather-title">🌤️ Weather Overview</div>
				<div class="weather-subtitle">📍 Melbourne, AU | 🕒 Updated {datetime.now().strftime('%d %b %Y, %H:%M')}</div>
			</div>
			""",
			unsafe_allow_html=True,
		)

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
			st.write("🔁 Replace MockWeatherRepository.get_hourly_forecast() with real API response parsing.")
			st.write("📦 Keep fields: time, temperature_c, humidity, wind_kmh, description.")
			st.write("✅ Chart and metric rendering can stay unchanged after API wiring.")


weather_page = WeatherPage(weather_repository=MockWeatherRepository())
weather_page.render()