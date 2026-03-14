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
# Helper functions
# ==========================================
def get_countries():
    return all_countries

def get_cities(country):
    return country_to_cities.get(country, [])

# ==========================================
# Session state init
# ==========================================
countries = get_countries()

if "country" not in st.session_state:
    st.session_state.country = "Australia" if "Australia" in countries else countries[0]

initial_cities = get_cities(st.session_state.country)

if "city" not in st.session_state:
    st.session_state.city = initial_cities[0] if initial_cities else ""

if "saved_country" not in st.session_state:
    st.session_state.saved_country = st.session_state.country

if "saved_city" not in st.session_state:
    st.session_state.saved_city = st.session_state.city

# ==========================================
# UI
# ==========================================
col1, col2 = st.columns(2)

# -------- Country --------
with col1:
    selected_country = st.selectbox(
        "Country",
        options=countries,
        index=countries.index(st.session_state.country)
        if st.session_state.country in countries else 0
    )

if selected_country != st.session_state.country:
    st.session_state.country = selected_country
    updated_cities = get_cities(selected_country)
    st.session_state.city = updated_cities[0] if updated_cities else ""

# -------- City --------
filtered_cities = get_cities(st.session_state.country)

with col2:
    if filtered_cities:
        selected_city = st.selectbox(
            "City",
            options=filtered_cities,
            index=filtered_cities.index(st.session_state.city)
            if st.session_state.city in filtered_cities else 0
        )
    else:
        selected_city = ""
        st.selectbox("City", options=["No city data available"], disabled=True)

if selected_city != st.session_state.city:
    st.session_state.city = selected_city

st.markdown("")

# -------- Save button --------
if st.button("Save Changes", use_container_width=True):
    st.session_state.saved_country = st.session_state.country
    st.session_state.saved_city = st.session_state.city
    st.success("Location saved successfully.")

# ==========================================
# Summary box
# ==========================================
st.markdown("### Summary")

summary_html = f"""
<div style="
    border: 1px solid #dcdcdc;
    border-radius: 12px;
    padding: 20px;
    background-color: #f8f9fa;
    margin-top: 10px;
">
    <h4 style="margin-top: 0;">Saved Location</h4>
    <p><strong>Country:</strong> {st.session_state.saved_country or 'N/A'}</p>
    <p><strong>City:</strong> {st.session_state.saved_city or 'N/A'}</p>
</div>
"""

st.markdown(summary_html, unsafe_allow_html=True)