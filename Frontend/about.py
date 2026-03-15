import streamlit as st

st.set_page_config(page_title='About Taylr', page_icon='ℹ️', layout='wide')

st.markdown(
    """
    <style>
    :root {
        --ink: #0f172a;
        --muted: #475569;
        --card-border: rgba(148, 163, 184, 0.24);
        --card-bg: rgba(255, 255, 255, 0.96);
    }

    @keyframes aboutFadeUp {
        from {
            opacity: 0;
            transform: translateY(18px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .about-shell {
        animation: aboutFadeUp 0.55s ease-out both;
    }

    .about-hero {
        border-radius: 22px;
        padding: 1.3rem 1.35rem;
        text-align: center;
        border: 1px solid var(--card-border);
        background:
            radial-gradient(circle at 12% 18%, rgba(253, 224, 71, 0.30), transparent 48%),
            radial-gradient(circle at 87% 13%, rgba(125, 211, 252, 0.35), transparent 42%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
        box-shadow: 0 18px 38px rgba(15, 23, 42, 0.08);
        margin-bottom: 0.9rem;
    }

    .about-hero h1 {
        margin: 0;
        color: var(--ink);
        font-size: 2.05rem;
        letter-spacing: 0.01em;
    }

    .about-hero h3 {
        margin: 0.35rem 0 0;
        color: #1e40af;
        font-size: 1.05rem;
        font-weight: 600;
    }

    .about-hero p {
        margin: 0.75rem 0 0;
        color: var(--muted);
        font-size: 0.98rem;
    }

    .hero-chips {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 0.85rem;
    }

    .hero-chip {
        border: 1px solid rgba(148, 163, 184, 0.26);
        border-radius: 999px;
        padding: 0.28rem 0.62rem;
        font-size: 0.8rem;
        color: #334155;
        background: rgba(255, 255, 255, 0.9);
    }

    .feature-card {
        border: 1px solid var(--card-border);
        border-radius: 16px;
        background: var(--card-bg);
        padding: 0.95rem 0.95rem 0.85rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
        height: 100%;
    }

    .feature-icon {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 0.35rem;
        font-size: 1.05rem;
        background: linear-gradient(135deg, rgba(219, 234, 254, 0.95), rgba(254, 249, 195, 0.95));
        border: 1px solid rgba(147, 197, 253, 0.45);
    }

    .feature-card h4 {
        margin: 0;
        color: var(--ink);
        font-size: 1rem;
    }

    .feature-card p {
        margin: 0.45rem 0 0;
        color: var(--muted);
        line-height: 1.45;
        font-size: 0.92rem;
    }

    div[data-testid="stHorizontalBlock"],
    div[data-testid="stAlert"],
    div[data-testid="stMarkdownContainer"] {
        animation: aboutFadeUp 0.48s ease-out both;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

left, center, right = st.columns([1, 2.2, 1])

with center:
    st.markdown('<div class="about-shell">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="about-hero">
            <h1>Meet Taylr 🪡</h1>
            <h3>Your Personal Wardrobe Architect</h3>
            <p><strong>Stop saying "I have nothing to wear."</strong><br>Taylr helps you rediscover your closet and dress smarter every day.</p>
            <div class="hero-chips">
                <span class="hero-chip">👗 Closet Sync</span>
                <span class="hero-chip">🌦️ Weather Smart</span>
                <span class="hero-chip">✨ AI Stylist</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.space(10)

    st.markdown(
        '**Taylr** is designed to take the guesswork out of getting dressed. By combining digital wardrobe organization with real-time weather context, it helps you make the most of the clothes you already own.'
    )

    st.divider()
    st.subheader('Core Features')

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">🧺</div>
                <h4>Digital Closet</h4>
                <p>Digitise your wardrobe and keep every piece searchable by category, color, and style. Skip accidental duplicate buys.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">📒</div>
                <h4>The Lookbook</h4>
                <p>Create and save outfit combinations for workdays, events, and weekend plans so your next look is ready in seconds.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-icon">🧠</div>
                <h4>Smart Suggestions</h4>
                <p>Weather-sync recommendations help you stay comfortable and stylish, from warm afternoons to cold, rainy mornings.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.success('Built for UniHack 2026 - crafted to give every outfit a better fit.')

    st.markdown('</div>', unsafe_allow_html=True)
