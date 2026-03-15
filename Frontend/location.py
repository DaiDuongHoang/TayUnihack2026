import streamlit as st
import pycountry
import geonamescache
from Authentication import is_authenticated, login_screen
from data_backend import get_user_location, save_user_location
from database import DEFAULT_LOCATION

if not is_authenticated():
    login_screen(
        title="Sign in to manage location",
        description="Use Google or your local email/password account to continue.",
    )
    st.stop()

# CSS animations
st.html("""
<style>
/* Slide-fade-DOWN keyframe */
@keyframes fadeSlideDownSettle {
    0% {
        opacity: 0;
        transform: translateY(-20px);
    }
    60% {
        opacity: 1;
        transform: translateY(4px);
    }
    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

.location-title {
    margin: 0;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

/* Apply to all buttons */
div[data-testid="stButton"] button {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Apply to bordered column/grid boxes */
div[data-testid="stColumn"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stColumn"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

/* Apply to horizontal divider */
div[data-testid="stDivider"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.3s both;
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
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stAlert"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}
</style>
""")

st.markdown('<h1 class="location-title">🗺️ My Location</h1>', unsafe_allow_html=True)

# Load country + city data
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


# Helper
def get_countries():
    return all_countries


def get_cities(country):
    return country_to_cities.get(country, [])


# Session state
countries = get_countries()
# any authenticated email: local or Google
raw_user_email = st.session_state.get("local_user") or getattr(st.user, "email", None)
user_email = str(raw_user_email or "").strip().lower() or None

# defaults from database
DEFAULT_COUNTRY, DEFAULT_CITY = DEFAULT_LOCATION[0], DEFAULT_LOCATION[1]


def _is_legacy_default_location(country: str, city: str) -> bool:
    return country.strip() == DEFAULT_COUNTRY and city.strip() == DEFAULT_CITY

if "location_owner" not in st.session_state:
    st.session_state.location_owner = None

if "location_explicitly_saved" not in st.session_state:
    st.session_state.location_explicitly_saved = False

if st.session_state.get("location_owner") != user_email:
    st.session_state.location_explicitly_saved = False

required_keys = (
    "country",
    "city",
    "saved_country",
    "saved_city",
    "location_explicitly_saved",
)
needs_bootstrap = (
    st.session_state.get("location_owner") != user_email
    or any(key not in st.session_state for key in required_keys)
)

if needs_bootstrap:
    stored_location = get_user_location(user_email) if user_email else None
    stored_country = (stored_location or {}).get("country", "").strip()
    stored_city = (stored_location or {}).get("city", "").strip()
    has_stored_values = bool(stored_country or stored_city)
    legacy_default_saved = _is_legacy_default_location(stored_country, stored_city)
    has_saved_location = has_stored_values and not legacy_default_saved

    default_country = DEFAULT_COUNTRY if DEFAULT_COUNTRY in countries else countries[0]
    default_city = ""

    if has_saved_location and stored_country in countries:
        default_country = stored_country
        has_saved_location = True

    default_cities = get_cities(default_country)
    if has_saved_location and stored_city in default_cities:
        default_city = stored_city
        has_saved_location = True
    elif DEFAULT_CITY in default_cities:
        default_city = DEFAULT_CITY
    elif default_cities:
        default_city = default_cities[0]

    st.session_state.country = default_country
    st.session_state.city = default_city
    st.session_state.saved_country = default_country if has_saved_location else ""
    st.session_state.saved_city = default_city if has_saved_location else ""
    st.session_state.location_explicitly_saved = has_saved_location
    st.session_state.location_owner = user_email

if "country" not in st.session_state:
    st.session_state.country = (
        DEFAULT_COUNTRY if DEFAULT_COUNTRY in countries else countries[0]
    )

cities = get_cities(st.session_state.country)

if "city" not in st.session_state:
    if DEFAULT_CITY in cities:
        st.session_state.city = DEFAULT_CITY
    else:
        st.session_state.city = cities[0] if cities else ""

if "saved_country" not in st.session_state:
    st.session_state.saved_country = ""

if "saved_city" not in st.session_state:
    st.session_state.saved_city = ""

if (
    not st.session_state.get("location_explicitly_saved", False)
    and _is_legacy_default_location(
        st.session_state.get("saved_country", ""),
        st.session_state.get("saved_city", ""),
    )
):
    st.session_state.saved_country = ""
    st.session_state.saved_city = ""

# UI
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
if st.button("**Save Changes**", width='stretch', type="primary"):
    st.session_state.saved_country = st.session_state.country
    st.session_state.saved_city = st.session_state.city
    st.session_state.location_explicitly_saved = True
    save_email = user_email
    save_ok = False
    if save_email:
        save_ok = save_user_location(
            save_email,
            st.session_state.saved_country,
            st.session_state.saved_city,
        )
        st.session_state.location_owner = user_email

    if save_ok:
        st.session_state.location_saved_toast = True
    elif save_email:
        st.session_state.location_explicitly_saved = False
        st.warning("Could not persist location right now. Please try again.")
    else:
        st.info("Location is stored for this session only in guest mode.")

if st.session_state.pop("location_saved_toast", False):
    st.toast("**Location saved!**", icon="✅", duration="short")

# Summary (STREAMLIT VERSION)

st.divider()

st.subheader("📍 Chosen Location")

summary_container = st.container(border=True)

with summary_container:
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Country", value=st.session_state.saved_country or "Not set")

    with col2:
        st.metric(label="City/Suburb", value=st.session_state.saved_city or "Not set")
