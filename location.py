import streamlit as st
import pycountry
import geonamescache


st.html("""
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
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Apply to bordered column/grid boxes */
div[data-testid="stColumn"] {
    animation: slideFadeDown 0.4s ease forwards;
}

/* Apply to st.container(border=True) boxes */
div[data-testid="stVerticalBlockBorderWrapper"] {
    animation: slideFadeDown 0.4s ease forwards;
    opacity: 0;
}

/* Apply to horizontal divider */
div[data-testid="stDivider"] {
    animation: slideFadeDown 0.4s ease 0.3s forwards;
    opacity: 0;
}

/* Stagger for buttons */
div[data-testid="stButton"]:nth-child(1) button { animation-delay: 0.0s; }
div[data-testid="stButton"]:nth-child(2) button { animation-delay: 0.1s; }
div[data-testid="stButton"]:nth-child(3) button { animation-delay: 0.2s; }
div[data-testid="stButton"]:nth-child(4) button { animation-delay: 0.3s; }

/* Stagger for grid boxes (columns) */
div[data-testid="stColumn"]:nth-child(1) { animation-delay: 0.0s; }
div[data-testid="stColumn"]:nth-child(2) { animation-delay: 0.1s; }
div[data-testid="stColumn"]:nth-child(3) { animation-delay: 0.2s; }
div[data-testid="stColumn"]:nth-child(4) { animation-delay: 0.3s; }

/* Stagger for bordered containers */
div[data-testid="stVerticalBlockBorderWrapper"]:nth-child(1) { animation-delay: 0.0s; }
div[data-testid="stVerticalBlockBorderWrapper"]:nth-child(2) { animation-delay: 0.1s; }
div[data-testid="stVerticalBlockBorderWrapper"]:nth-child(3) { animation-delay: 0.2s; }
div[data-testid="stVerticalBlockBorderWrapper"]:nth-child(4) { animation-delay: 0.3s; }

/* Keep hover effect on buttons */
div[data-testid="stButton"] button:hover {
    transform: scale(1.03);
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
}
</style>
""")

st.set_page_config(page_title="Global Location Dashboard", layout="wide")

st.title("🗺️ My Location")

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
        "Country", countries, index=countries.index(st.session_state.country)
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
            "City/Suburb",
            filtered_cities,
            index=filtered_cities.index(st.session_state.city),
        )
    else:
        selected_city = ""
        st.selectbox("City/Suburb", ["No data"], disabled=True)

if selected_city != st.session_state.city:
    st.session_state.city = selected_city

st.markdown("")

# Save button
if st.button("**Save Changes**", use_container_width=True, type="primary"):
    st.session_state.saved_country = st.session_state.country
    st.session_state.saved_city = st.session_state.city
    st.success("Location saved!")

# ==========================================
# Summary (STREAMLIT VERSION)
# ==========================================

st.divider()

st.subheader("📍 Chosen Location")

summary_container = st.container(border=True)

with summary_container:
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Country", value=st.session_state.saved_country or "N/A")

    with col2:
        st.metric(label="City/Suburb", value=st.session_state.saved_city or "N/A")
