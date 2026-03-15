import streamlit as st

st.set_page_config(page_title="About Us", layout="centered")

css = """
<style>
/* Gradient box container */
.st-key-gradient-box {
    background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460);
    color: white;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}
.st-key-gradient-box h1 {
    color: white !important;
    font-size: 2.5rem;
    margin: 0;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.05s both;
}

/* Description container */
.st-key-description-box {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.2s both;
}

/* Target text elements inside description box */
.st-key-description-box p,
.st-key-description-box li,
.st-key-description-box strong {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.3s both;
}

@keyframes fadeSlideDownSettle {
    0% {
        opacity: 0;
        transform: translateY(-20px);
    }
    60% {
        opacity: 1;
        transform: translateY(4px);   /* subtle slide UP past resting point */
    }
    100% {
        opacity: 1;
        transform: translateY(0);     /* settles back to natural position */
    }
}
</style>
"""
st.html(css)

# Gradient box for "About Us" title
with st.container(key="gradient-box"):
    st.markdown("# About Taylr 🪡🧵")

# Normal body text for description
with st.container(key="description-box"):
    st.markdown("""
Taylr is a personal wardrobe assistant that helps you manage your clothing items, plan outfits, and get weather-based recommendations.

**What this app does:**
- **Wardrobe Management**: Keep track of your clothing items, categorize them, and easily view your wardrobe inventory.
- **Outfit Planning**: Create and save outfit combinations for different occasions and seasons.
""")

