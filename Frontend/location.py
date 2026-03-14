import streamlit as st
import pycountry
import geonamescache

# CSS animations
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
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stColumn"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

/* Apply to horizontal divider */
div[data-testid="stDivider"] {
    animation: slideFadeDown 0.4s ease 0.3s forwards;
    opacity: 0; /* Start hidden until animation runs */
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
    transform: translateY(-3px) scale(1.07);
    box-shadow: 0px 10px 22px rgba(0, 0, 0, 0.28);
}

/* Dedicated animation for the Go Back button */
@keyframes backButtonFloat {
    0%,
    100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-7px);
    }
}

@keyframes backButtonWiggle {
    0% {
        transform: translateX(-6px) scale(1.09) rotate(0deg);
    }
    25% {
        transform: translateX(-10px) scale(1.11) rotate(-2deg);
    }
    50% {
        transform: translateX(-6px) scale(1.12) rotate(2deg);
    }
    75% {
        transform: translateX(-10px) scale(1.11) rotate(-1deg);
    }
    100% {
        transform: translateX(-6px) scale(1.09) rotate(0deg);
    }
}

.st-key-back_button button {
    animation: backButtonFloat 1.8s ease-in-out infinite;
    border: 1px solid rgba(59, 130, 246, 0.35);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}

.st-key-back_button button:hover {
    animation: backButtonWiggle 0.45s ease-in-out infinite;
    box-shadow: 0 14px 30px rgba(59, 130, 246, 0.55);
    filter: brightness(1.14) saturate(1.2);
}

/* Apply slideFadeDown animation to st.success (alert elements) */
div[data-testid="stAlert"] {
    animation: slideFadeDown 0.4s ease forwards;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stAlert"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

/* Compact centered save notification */
.saved-pill {
    display: table;
    margin: 0.5rem auto 0;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.84rem;
    font-weight: 600;
    color: #065f46;
    background: #d1fae5;
    border: 1px solid #86efac;
    animation: slideFadeDown 0.35s ease forwards;
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
    st.markdown(
        "<div class='saved-pill'>✅ Location saved!</div>",
        unsafe_allow_html=True,
    )

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
