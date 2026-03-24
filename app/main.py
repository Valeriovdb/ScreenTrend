"""
ScreenTrend — Streamlit app
"""

import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="ScreenTrend", page_icon="🎬", layout="wide")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

RELEASE_TYPE_LABELS = {
    "theatrical":       "Theatrical only",
    "theatrical_first": "Theatrical → Streaming",
    "streaming_only":   "Streaming only",
    "unknown":          "Unknown",
}
RELEASE_TYPE_COLORS = {
    "Theatrical only":         "#2563eb",
    "Theatrical → Streaming":  "#7c3aed",
    "Streaming only":          "#16a34a",
    "Unknown":                 "#9ca3af",
}


@st.cache_resource
def get_db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data(ttl=120)
def load_data() -> pd.DataFrame:
    db = get_db()
    response = db.table("movies").select("*").execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return df

    df["themes"] = df["themes"].apply(lambda x: x if isinstance(x, list) else [])
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")
    df["release_type_label"] = df["release_type"].map(RELEASE_TYPE_LABELS).fillna("Unknown")
    return df


# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("ScreenTrend")
st.sidebar.caption("Film analytics · 2020–2026")

page = st.sidebar.radio(
    "View",
    ["Theme Intelligence", "Market Overview", "Success Explorer", "About"],
)

df_all = load_data()

if df_all.empty:
    st.warning("No data loaded. Run the pipeline first.")
    st.stop()

years = sorted(df_all["release_year"].dropna().unique().astype(int).tolist())

# ── Shared filters ─────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**Filters**")

selected_years = st.sidebar.select_slider(
    "Release years", options=years, value=(min(years), max(years))
)

languages = ["All"] + sorted(df_all["original_language"].dropna().unique().tolist())
selected_lang = st.sidebar.selectbox("Language", languages)

df = df_all[
    (df_all["release_year"] >= selected_years[0]) &
    (df_all["release_year"] <= selected_years[1])
].copy()
if selected_lang != "All":
    df = df[df["original_language"] == selected_lang]


# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 — THEME INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════
if page == "Theme Intelligence":
    st.title("Theme Intelligence")
    st.caption(f"{len(df):,} films · {selected_years[0]}–{selected_years[1]}")

    df_with_themes = df[df["themes"].apply(lambda x: len(x) > 0)]
    coverage = len(df_with_themes) / len(df) * 100 if len(df) > 0 else 0

    if coverage < 5:
        st.info("Theme extraction is still running. Check back shortly — this page will update automatically.")
        st.progress(coverage / 100, text=f"{coverage:.0f}% of films tagged")
        st.stop()

    if coverage < 100:
        st.info(f"Theme extraction {coverage:.0f}% complete — results will update as more films are tagged.")

    exploded = df_with_themes.explode("themes").dropna(subset=["themes"])
    theme_counts = (
        exploded.groupby("themes").size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    top_themes = theme_counts.head(10)["themes"].tolist()

    # ── Row 1: Most recurrent + frequency over time ────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most recurrent themes")
        fig = px.bar(
            theme_counts.head(15),
            x="count", y="themes", orientation="h",
            color="count", color_continuous_scale="Blues",
            labels={"themes": "", "count": "Films"},
        )
        fig.update_layout(
            showlegend=False, coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Theme frequency over time")
        theme_year = (
            exploded[exploded["themes"].isin(top_themes)]
            .groupby(["release_year", "themes"]).size()
            .reset_index(name="count")
        )
        fig2 = px.line(
            theme_year, x="release_year", y="count", color="themes",
            markers=True,
            labels={"release_year": "Year", "count": "Films", "themes": "Theme"},
        )
        fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Theme density heatmap ───────────────────────────────────────
    st.subheader("Theme density by quarter")
    exploded["quarter"] = pd.to_datetime(
        df_with_themes["release_date"].reindex(exploded.index), errors="coerce"
    ).dt.to_period("Q").astype(str)

    pivot = (
        exploded[exploded["themes"].isin(top_themes)]
        .groupby(["quarter", "themes"]).size()
        .unstack(fill_value=0)
        .sort_index()
    )
    fig3 = px.imshow(
        pivot.T,
        color_continuous_scale="Blues",
        aspect="auto",
        labels=dict(x="Quarter", y="Theme", color="Films"),
    )
    fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig3, use_container_width=True)

    # ── Row 3: Theme vs IMDB rating scatter ────────────────────────────────
    st.subheader("Theme vs IMDB rating")
    theme_scores = (
        exploded.groupby("themes")["imdb_rating"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_rating", "count": "films"})
        .query("films >= 5")
    )
    fig4 = px.scatter(
        theme_scores, x="films", y="avg_rating",
        text="themes", size="films",
        color="avg_rating", color_continuous_scale="RdYlGn",
        labels={"films": "Number of films", "avg_rating": "Avg IMDB rating", "themes": "Theme"},
        range_color=[5, 8],
    )
    fig4.update_traces(textposition="top center")
    fig4.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig4, use_container_width=True)

    # ── Film table ─────────────────────────────────────────────────────────
    st.subheader("Browse by theme")
    selected_theme = st.selectbox(
        "Select theme", ["All"] + sorted(theme_counts["themes"].tolist())
    )
    if selected_theme != "All":
        tbl = (
            exploded[exploded["themes"] == selected_theme]
            [["title", "release_year", "original_language", "director",
              "imdb_rating", "revenue", "narrative_pattern"]]
            .drop_duplicates("title")
            .sort_values("release_year", ascending=False)
        )
    else:
        tbl = df[["title", "release_year", "original_language", "director",
                  "imdb_rating", "revenue", "themes"]].sort_values("release_year", ascending=False)
    st.dataframe(tbl, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 — MARKET OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
elif page == "Market Overview":
    st.title("Market Overview")
    st.caption(f"{len(df):,} films · {selected_years[0]}–{selected_years[1]}")

    # ── KPI row ────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total films", f"{len(df):,}")
    k2.metric("Languages", df["original_language"].nunique())
    streaming = df[df["release_type"] == "streaming_only"]
    k3.metric("Streaming only", f"{len(streaming):,}", f"{len(streaming)/len(df)*100:.0f}%")
    theatrical = df[df["release_type"].isin(["theatrical", "theatrical_first"])]
    k4.metric("Had theatrical run", f"{len(theatrical):,}", f"{len(theatrical)/len(df)*100:.0f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # ── Release volume by year ─────────────────────────────────────────────
    with col1:
        st.subheader("Releases per year")
        by_year = df.groupby(["release_year", "release_type_label"]).size().reset_index(name="count")
        fig = px.bar(
            by_year, x="release_year", y="count", color="release_type_label",
            color_discrete_map=RELEASE_TYPE_COLORS,
            labels={"release_year": "Year", "count": "Films", "release_type_label": "Release type"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # ── Release type share over time ───────────────────────────────────────
    with col2:
        st.subheader("Release type share over time")
        pivot = (
            df.groupby(["release_year", "release_type_label"]).size()
            .unstack(fill_value=0)
        )
        pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
        pivot_pct = pivot_pct.reset_index().melt(
            id_vars="release_year", var_name="release_type_label", value_name="pct"
        )
        fig2 = px.area(
            pivot_pct, x="release_year", y="pct", color="release_type_label",
            color_discrete_map=RELEASE_TYPE_COLORS,
            labels={"release_year": "Year", "pct": "% of releases", "release_type_label": "Type"},
        )
        fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    # ── Language breakdown ─────────────────────────────────────────────────
    with col3:
        st.subheader("Top languages")
        lang = df["original_language"].value_counts().head(12).reset_index()
        lang.columns = ["language", "count"]
        fig3 = px.bar(
            lang, x="count", y="language", orientation="h",
            color="count", color_continuous_scale="Purples",
            labels={"language": "", "count": "Films"},
        )
        fig3.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Genre breakdown ────────────────────────────────────────────────────
    with col4:
        st.subheader("Top genres")
        genre_exploded = df["genres"].dropna().str.split(", ").explode()
        genre_counts = genre_exploded.value_counts().head(12).reset_index()
        genre_counts.columns = ["genre", "count"]
        fig4 = px.bar(
            genre_counts, x="count", y="genre", orientation="h",
            color="count", color_continuous_scale="Greens",
            labels={"genre": "", "count": "Films"},
        )
        fig4.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Streaming platform breakdown ───────────────────────────────────────
    st.subheader("Streaming platforms")
    platforms = df["streaming_platform"].dropna()
    if platforms.empty:
        st.info("Watch provider data still loading.")
    else:
        plat_counts = platforms.value_counts().reset_index()
        plat_counts.columns = ["platform", "count"]
        fig5 = px.pie(
            plat_counts, names="platform", values="count",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig5.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig5, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 3 — SUCCESS EXPLORER
# ══════════════════════════════════════════════════════════════════════════
elif page == "Success Explorer":
    st.title("Success Explorer")
    st.caption("Compare what drives commercial vs critical outcomes")

    # ── Filters ────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        all_genres = sorted(
            set(g for gs in df["genres"].dropna().str.split(", ") for g in gs)
        )
        sel_genre = st.selectbox("Genre", ["All"] + all_genres)
    with fc2:
        sel_release_type = st.selectbox(
            "Release type",
            ["All"] + list(RELEASE_TYPE_LABELS.values()),
        )
    with fc3:
        sel_min_rating = st.slider("Min IMDB rating", 0.0, 10.0, 0.0, 0.5)

    dff = df.copy()
    if sel_genre != "All":
        dff = dff[dff["genres"].str.contains(sel_genre, na=False)]
    if sel_release_type != "All":
        dff = dff[dff["release_type_label"] == sel_release_type]
    if sel_min_rating > 0:
        dff = dff[dff["imdb_rating"] >= sel_min_rating]

    st.caption(f"{len(dff):,} films match filters")
    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── IMDB rating distribution ───────────────────────────────────────────
    with col1:
        st.subheader("IMDB rating distribution")
        fig = px.histogram(
            dff, x="imdb_rating", nbins=30,
            color_discrete_sequence=["#2563eb"],
            labels={"imdb_rating": "IMDB rating", "count": "Films"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # ── Box office distribution ────────────────────────────────────────────
    with col2:
        st.subheader("Box office distribution (theatrical films)")
        theatrical_dff = dff[dff["revenue"].notna() & (dff["revenue"] > 1_000_000)]
        if theatrical_dff.empty:
            st.info("No theatrical films in this filter set.")
        else:
            fig2 = px.histogram(
                theatrical_dff, x="revenue", nbins=40,
                color_discrete_sequence=["#7c3aed"],
                labels={"revenue": "Worldwide revenue ($)", "count": "Films"},
            )
            fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig2, use_container_width=True)

    # ── Genre vs IMDB rating ───────────────────────────────────────────────
    st.subheader("Genre vs IMDB rating")
    genre_exp = dff.copy()
    genre_exp["genre_list"] = genre_exp["genres"].str.split(", ")
    genre_exp = genre_exp.explode("genre_list").dropna(subset=["genre_list", "imdb_rating"])
    genre_stats = (
        genre_exp.groupby("genre_list")["imdb_rating"]
        .agg(["mean", "median", "count"])
        .reset_index()
        .rename(columns={"genre_list": "genre", "mean": "avg", "median": "med", "count": "films"})
        .query("films >= 5")
        .sort_values("avg", ascending=False)
    )
    fig3 = px.bar(
        genre_stats, x="genre", y="avg",
        error_y=genre_stats["avg"] - genre_stats["med"],
        color="avg", color_continuous_scale="RdYlGn",
        labels={"genre": "Genre", "avg": "Avg IMDB rating"},
        range_color=[5, 8],
    )
    fig3.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig3, use_container_width=True)

    # ── Rating vs Revenue scatter ──────────────────────────────────────────
    st.subheader("IMDB rating vs box office")
    scatter_df = dff[
        dff["revenue"].notna() & (dff["revenue"] > 1_000_000) & dff["imdb_rating"].notna()
    ].copy()
    scatter_df["revenue_m"] = scatter_df["revenue"] / 1_000_000

    if scatter_df.empty:
        st.info("No theatrical films with revenue data in this filter set.")
    else:
        fig4 = px.scatter(
            scatter_df, x="imdb_rating", y="revenue_m",
            hover_name="title", color="release_type_label",
            color_discrete_map=RELEASE_TYPE_COLORS,
            opacity=0.7,
            labels={
                "imdb_rating": "IMDB rating",
                "revenue_m": "Worldwide revenue ($M)",
                "release_type_label": "Release type",
            },
        )
        fig4.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig4, use_container_width=True)

    # ── Top films table ────────────────────────────────────────────────────
    st.subheader("Films in this filter set")
    tbl_cols = ["title", "release_year", "original_language", "genres",
                "director", "imdb_rating", "revenue", "release_type_label"]
    tbl = (
        dff[[c for c in tbl_cols if c in dff.columns]]
        .sort_values("imdb_rating", ascending=False)
    )
    st.dataframe(tbl, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 4 — ABOUT
# ══════════════════════════════════════════════════════════════════════════
elif page == "About":
    st.title("About ScreenTrend")
    st.markdown("""
**ScreenTrend** analyzes 2020–2026 films to understand how release type, talent, language,
genre, and AI-derived themes relate to commercial success, critical reception, and awards recognition.

---

### Data sources
| Source | Used for |
|---|---|
| Kaggle TMDB dataset (alanvourch) | Core metadata, revenue, cast, director |
| TMDB API | Streaming provider / watch provider data |
| IMDB via dataset | Ratings, vote counts |
| OpenAI GPT-4o-mini | Theme extraction from plot overviews |

### Release type classification
- **Theatrical only** — revenue > $1M, no streaming platform found
- **Theatrical → Streaming** — revenue > $1M, later available on streaming
- **Streaming only** — revenue = 0, available on streaming platform
- **Unknown** — insufficient data to classify

### Theme extraction
Themes are extracted from TMDB plot overviews using GPT-4o-mini.
Each film is tagged with 1–3 themes from a defined taxonomy, with a confidence score per tag.
Theme tags are model-generated and carry uncertainty.

### Limitations
- 2020–2026 is a limited window for long-cycle pattern detection
- Box office data is incomplete for streaming-only films
- Awards data is not yet loaded
- Theme tags depend on overview quality and are not ground truth
- This product identifies associations, not causal relationships
    """)
