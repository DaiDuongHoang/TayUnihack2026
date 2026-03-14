import streamlit as st
import pycountry
import geonamescache

st.set_page_config(page_title="Global Location Dashboard", layout="wide")

st.title("Location Dashboard")

# ==========================================
# Load country + city data
# ==========================================
gc = geonamescache.GeonamesCache()
cities_data = gc.get_cities()

country_name_to_code = {}
for country in pycountry.countries:
    if hasattr(country, "alpha_2"):
        country_name_to_code[country.name] = country.alpha_2

country_code_to_name = {v: k for k, v in country_name_to_code.items()}
all_countries = sorted(country_name_to_code.keys())

country_to_cities = {}

for city_info in cities_data.values():
    country_code = city_info.get("countrycode")
    city_name = city_info.get("name")

    if not country_code or not city_name:
        continue

    country_name = country_code_to_name.get(country_code)
    if not country_name:
        continue

    if country_name not in country_to_cities:
        country_to_cities[country_name] = set()

    country_to_cities[country_name].add(city_name)

for country_name in country_to_cities:
    country_to_cities[country_name] = sorted(list(country_to_cities[country_name]))

# ==========================================
# Helper
# ==========================================
def get_countries():
    return all_countries

def get_cities(country):
    return country_to_cities.get(country, [])

# ==========================================
# Session state
# ==========================================
countries = get_countries()

if "country" not in st.session_state:
    st.session_state.country = countries[0]

cities = get_cities(st.session_state.country)

if "city" not in st.session_state:
    st.session_state.city = cities[0] if cities else ""

if "saved_country" not in st.session_state:
    st.session_state.saved_country = st.session_state.country

if "saved_city" not in st.session_state:
    st.session_state.saved_city = st.session_state.city

# ==========================================
# UI
# ==========================================
col1, col2 = st.columns(2)

# Country
with col1:
    selected_country = st.selectbox(
        "Country",
        countries,
        index=countries.index(st.session_state.country)
    )

if selected_country != st.session_state.country:
    st.session_state.country = selected_country
    new_cities = get_cities(selected_country)
    st.session_state.city = new_cities[0] if new_cities else ""

# City
filtered_cities = get_cities(st.session_state.country)

with col2:
    if filtered_cities:
        selected_city = st.selectbox(
            "City",
            filtered_cities,
            index=filtered_cities.index(st.session_state.city)
        )
    else:
        selected_city = ""
        st.selectbox("City", ["No data"], disabled=True)

if selected_city != st.session_state.city:
    st.session_state.city = selected_city

st.markdown("")

# Save button
if st.button("Save Changes", use_container_width=True):
    st.session_state.saved_country = st.session_state.country
    st.session_state.saved_city = st.session_state.city
    st.success("Location saved")

# ==========================================
# Summary (STREAMLIT VERSION)
# ==========================================

st.divider()

st.subheader("Summary")

summary_container = st.container(border=True)

with summary_container:

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="Country",
            value=st.session_state.saved_country or "N/A"
        )

    with col2:
        st.metric(
            label="City",
            value=st.session_state.saved_city or "N/A"
        )