"""
ScreenTrend — Streamlit app
"""

import os
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="ScreenTrend", page_icon="🎬", layout="wide")

st.markdown("""
<style>
/* ── Base ─────────────────────────────────────────────────────────── */
.block-container { padding-top: 1.8rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
p { font-size: 0.85rem !important; }

/* ── Sidebar ─────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] { background: #1e293b !important; border-right: none !important; }
section[data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1rem !important; }
section[data-testid="stSidebar"] .stMarkdown strong { color: #f1f5f9 !important; font-size: 0.88rem; letter-spacing: 0.03em; }
section[data-testid="stSidebar"] .stCaption p { color: #475569 !important; font-size: 0.70rem !important; }
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] .stMarkdown strong { color: #f1f5f9 !important; }
section[data-testid="stSidebar"] .stMarkdown p { color: #475569 !important; font-size: 0.65rem !important; text-transform: uppercase; letter-spacing: 0.09em; font-weight: 600; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stSlider label { color: #64748b !important; font-size: 0.75rem !important; }
section[data-testid="stSidebar"] hr { border-color: #334155 !important; margin: 0.75rem 0 !important; }

/* ── KPI cards ───────────────────────────────────────────────────── */
.kpi-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    border: 1px solid #f1f5f9;
    height: 100%;
}
.kpi-label {
    font-size: 0.62rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.03em;
    line-height: 1.0;
}
.kpi-sub { font-size: 0.69rem; color: #94a3b8; margin-top: 6px; line-height: 1.4; }

/* ── Signal cards ────────────────────────────────────────────────── */
.signal-card {
    background: #f8fafc;
    border-radius: 8px;
    padding: 14px 16px;
    border: 1px solid #f1f5f9;
    height: 100%;
}
.signal-badge {
    display: inline-block;
    font-size: 0.58rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    padding: 2px 7px;
    border-radius: 3px;
    margin-bottom: 8px;
}
.badge-up      { background: #dcfce7; color: #15803d; }
.badge-down    { background: #fee2e2; color: #b91c1c; }
.badge-neutral { background: #f1f5f9; color: #475569; }
.badge-caution { background: #fef3c7; color: #b45309; }
.signal-text   { font-size: 0.80rem; color: #334155; line-height: 1.55; }

/* ── Section headers ─────────────────────────────────────────────── */
.section-label {
    font-size: 0.62rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 2.4rem 0 1rem 0;
    padding-left: 10px;
    border-left: 2px solid #0ea5e9;
}

/* ── Chart label ─────────────────────────────────────────────────── */
.chart-label {
    font-size: 0.76rem;
    font-weight: 600;
    color: #334155;
    letter-spacing: -0.01em;
    margin-bottom: 2px;
}

/* ── Insight block ───────────────────────────────────────────────── */
.insight-block {
    background: #f8fafc;
    border-left: 2px solid #0ea5e9;
    border-radius: 0 6px 6px 0;
    padding: 12px 16px;
    margin: 8px 0 16px 0;
    font-size: 0.82rem;
    color: #334155;
    line-height: 1.7;
}
.insight-caveat { font-size: 0.72rem; color: #64748b; margin-top: 8px; font-style: italic; }

/* ── Theme definition box ────────────────────────────────────────── */
.theme-definition-box {
    background: #f8fafc;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 0.82rem;
    color: #334155;
    line-height: 1.65;
    border: 1px solid #f1f5f9;
}
.theme-keywords { margin-top: 8px; font-size: 0.71rem; color: #64748b; }
</style>
""", unsafe_allow_html=True)

# ── Theme glossary ─────────────────────────────────────────────────────────
THEME_GLOSSARY = {
    "identity / belonging": {
        "definition": (
            "Characters searching for their place — in a family, culture, society, or within "
            "themselves. Includes immigrant stories, cultural displacement, and finding one's identity "
            "outside the mainstream."
        ),
        "keywords": ["self-discovery", "cultural identity", "outsider", "diaspora", "belonging"],
    },
    "power and control": {
        "definition": (
            "Stories about who holds power and how it is exercised, maintained, or challenged. "
            "Covers political thrillers, corporate hierarchies, dictatorships, and domestic coercion."
        ),
        "keywords": ["authority", "oppression", "manipulation", "regime", "coercion"],
    },
    "class conflict / critique of elites": {
        "definition": (
            "Films that pit social classes against each other, or that expose the contradictions and "
            "moral failures of the wealthy. Often satirical in tone."
        ),
        "keywords": ["wealth gap", "privilege", "social class", "satire", "inequality"],
    },
    "revenge": {
        "definition": (
            "A protagonist driven by the need to repay a specific wrong. Spans personal vendettas, "
            "vigilante justice, and long-arc retaliation stories."
        ),
        "keywords": ["vengeance", "retribution", "grudge", "justice", "violence"],
    },
    "grief and loss": {
        "definition": (
            "Loss — of a person, relationship, or way of life — shapes the story. Explores how "
            "characters cope, fail to move on, or are transformed by absence."
        ),
        "keywords": ["death", "mourning", "trauma", "absence", "healing"],
    },
    "family conflict": {
        "definition": (
            "Tension within family units — between parents and children, siblings, or across "
            "generations. Includes estrangement, buried secrets, and conflicts over inheritance or legacy."
        ),
        "keywords": ["parents", "siblings", "dysfunction", "legacy", "estrangement"],
    },
    "coming of age": {
        "definition": (
            "A young protagonist navigates a defining transition — first love, loss of innocence, "
            "or the crossing from adolescence into adult responsibility."
        ),
        "keywords": ["youth", "first love", "growth", "school", "transition"],
    },
    "survival": {
        "definition": (
            "Characters fighting to stay alive against nature, catastrophe, or other people. "
            "Includes wilderness survival, disaster films, and stories of endurance under oppression."
        ),
        "keywords": ["endurance", "wilderness", "catastrophe", "fight for life", "escape"],
    },
    "technology / ai": {
        "definition": (
            "Stories that interrogate what technology — especially artificial intelligence — does to "
            "human identity, labor, surveillance, and power."
        ),
        "keywords": ["artificial intelligence", "surveillance", "automation", "digital", "future"],
    },
    "social satire": {
        "definition": (
            "Films that use irony, absurdism, or dark comedy to expose hypocrisy and contradiction "
            "in social systems, institutions, or cultural norms."
        ),
        "keywords": ["irony", "absurdism", "dark comedy", "critique", "parody"],
    },
    "romance across difference": {
        "definition": (
            "Love stories where the protagonists are separated by class, culture, religion, or "
            "circumstance — and must navigate that distance."
        ),
        "keywords": ["forbidden love", "cross-cultural", "class barrier", "unlikely pair", "interracial"],
    },
    "justice / corruption": {
        "definition": (
            "Films about institutional failure, legal injustice, or individuals fighting corrupt "
            "systems — police, courts, governments, corporations. The system is the antagonist."
        ),
        "keywords": ["injustice", "corruption", "systemic failure", "whistleblower", "wrongful conviction"],
    },
    "war / trauma": {
        "definition": (
            "Stories set during or in the aftermath of armed conflict, focused on the psychological "
            "and human cost rather than military strategy."
        ),
        "keywords": ["combat", "PTSD", "occupation", "veterans", "civilian cost"],
    },
    "redemption": {
        "definition": (
            "A character who has caused serious harm seeks — and sometimes earns — a second chance. "
            "Involves confession, sacrifice, or a genuine moral reckoning."
        ),
        "keywords": ["second chance", "forgiveness", "atonement", "reform", "moral recovery"],
    },
    "isolation": {
        "definition": (
            "Characters cut off from society — physically, emotionally, or both. Explores loneliness, "
            "self-imposed exile, and the cost of disconnection from human community."
        ),
        "keywords": ["loneliness", "solitude", "exile", "disconnection", "alienation"],
    },
}

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

RELEASE_TYPE_LABELS = {
    "theatrical":       "Theatrical only",
    "theatrical_first": "Theatrical → Streaming",
    "streaming_only":   "Streaming only",
    "unknown":          "Unknown",
}
RELEASE_TYPE_COLORS = {
    "Theatrical only":         "#1d4ed8",
    "Theatrical → Streaming":  "#7c3aed",
    "Streaming only":          "#059669",
    "Unknown":                 "#cbd5e1",
}

QUAD_COLORS = {
    "Proven ground":  "#059669",
    "Hidden gems":    "#0ea5e9",
    "Crowded & weak": "#f59e0b",
    "Low signal":     "#e2e8f0",
}

ACCENT        = "#0ea5e9"
ACCENT_MUTED  = "#bae6fd"
SERIES_COLORS = ["#0ea5e9", "#8b5cf6", "#10b981", "#f59e0b", "#6366f1", "#14b8a6", "#f97316", "#ef4444"]

OUTCOME_COLS = {
    "IMDB rating":     "imdb_rating",
    "RT score":        "rt_score",
    "Metacritic":      "metacritic",
    "Box office ($M)": "revenue_m",
}


def fmt_outcome(val, col: str) -> str:
    """Format an outcome value for display."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    if col == "imdb_rating":  return f"{val:.2f}"
    if col == "rt_score":     return f"{val:.0f}%"
    if col == "metacritic":   return f"{val:.0f}"
    if col == "revenue_m":    return f"${val:.0f}M"
    return str(val)


@st.cache_resource
def get_db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    db = get_db()
    rows, offset, page_size = [], 0, 1000
    while True:
        batch = db.table("movies").select("*").range(offset, offset + page_size - 1).execute().data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["themes"] = df["themes"].apply(lambda x: x if isinstance(x, list) else [])
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")
    df["release_type_label"] = df["release_type"].map(RELEASE_TYPE_LABELS).fillna("Unknown")
    return df


def kpi(label, value, sub=""):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section(label):
    st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)


def chart_label(text: str):
    st.markdown(f'<div class="chart-label">{text}</div>', unsafe_allow_html=True)


def signal(badge_type: str, badge_text: str, body: str):
    """Render a signal card. badge_type: 'up' | 'down' | 'neutral' | 'caution'"""
    st.markdown(
        f'<div class="signal-card">'
        f'<span class="signal-badge badge-{badge_type}">{badge_text}</span>'
        f'<div class="signal-text">{body}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def chart_style(fig, height: int = None, hgrid: bool = True, vgrid: bool = False):
    """Apply the product chart style to any Plotly figure."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui,-apple-system,sans-serif", size=11, color="#475569"),
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(
            showgrid=vgrid,
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
            tickcolor="rgba(0,0,0,0)",
            tickfont=dict(size=10, color="#64748b"),
            title_font=dict(size=10, color="#94a3b8"),
        ),
        yaxis=dict(
            showgrid=hgrid,
            gridcolor="#f1f5f9",
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(size=10, color="#64748b"),
            title_font=dict(size=10, color="#94a3b8"),
        ),
        legend=dict(
            font=dict(size=10, color="#64748b"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
    )
    if height:
        fig.update_layout(height=height)
    return fig


def fmt_theme(t: str) -> str:
    return t.title()


# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.markdown("**ScreenTrend**")
st.sidebar.caption("Film analytics · 2020–2026")

page = st.sidebar.radio(
    "nav",
    ["Market Context", "Drivers", "Opportunities", "Methodology"],
    label_visibility="collapsed",
)

df_all = load_data()

if df_all.empty:
    st.warning("No data loaded. Run the pipeline first.")
    st.stop()

years = sorted(df_all["release_year"].dropna().unique().astype(int).tolist())

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters**")

selected_years = st.sidebar.select_slider(
    "Period", options=years, value=(min(years), max(years))
)

languages = ["All"] + sorted(df_all["original_language"].dropna().unique().tolist())
selected_lang = st.sidebar.selectbox("Language", languages)

all_genres = sorted(set(g for gs in df_all["genres"].dropna().str.split(", ") for g in gs))
selected_genre = st.sidebar.selectbox("Genre", ["All"] + all_genres)

release_type_opts = ["All"] + list(RELEASE_TYPE_LABELS.values())
selected_release_type = st.sidebar.selectbox("Release window", release_type_opts)

df = df_all[
    (df_all["release_year"] >= selected_years[0]) &
    (df_all["release_year"] <= selected_years[1])
].copy()
if selected_lang != "All":
    df = df[df["original_language"] == selected_lang]
if selected_genre != "All":
    df = df[df["genres"].str.contains(selected_genre, na=False)]
if selected_release_type != "All":
    df = df[df["release_type_label"] == selected_release_type]

# ── Shared computations ────────────────────────────────────────────────────
df["revenue_m"] = df["revenue"] / 1_000_000

# Genre exploded (for all pages)
genre_exp_df = (
    df.assign(genre=df["genres"].str.split(", "))
    .explode("genre")
    .dropna(subset=["genre"])
)

# Theme coverage
df_with_themes = df[df["themes"].apply(len) > 0]
total_tagged = len(df_with_themes)
coverage = total_tagged / len(df) * 100 if len(df) > 0 else 0
themes_available = coverage >= 5

# Theme trend computation (share-adjusted, midpoint split)
if themes_available:
    exploded = df_with_themes.explode("themes").dropna(subset=["themes"]).copy()
    exploded["quarter"] = (
        pd.to_datetime(df_with_themes["release_date"].reindex(exploded.index), errors="coerce")
        .dt.to_period("Q").astype(str)
    )

    mid_year = (selected_years[0] + selected_years[1]) / 2
    n_early = len(df_with_themes[df_with_themes["release_year"] <= mid_year])
    n_late  = len(df_with_themes[df_with_themes["release_year"] > mid_year])
    early_counts = exploded[exploded["release_year"] <= mid_year].groupby("themes").size()
    late_counts  = exploded[exploded["release_year"] > mid_year].groupby("themes").size()
    early_share  = (early_counts / n_early * 100) if n_early > 0 else pd.Series(dtype=float)
    late_share   = (late_counts  / n_late  * 100) if n_late  > 0 else pd.Series(dtype=float)
    share_delta  = (late_share - early_share).fillna(0)
    early_rank   = early_counts.rank(ascending=False, method="min")
    late_rank    = late_counts.rank(ascending=False, method="min")
    rank_delta   = (early_rank - late_rank).fillna(0).astype(int)

    theme_counts = (
        exploded.groupby("themes").size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    theme_counts["share_pct"]   = (theme_counts["count"] / total_tagged * 100).round(1)
    theme_counts["share_delta"] = theme_counts["themes"].map(share_delta).fillna(0).round(1)
    theme_counts["rank_change"] = theme_counts["themes"].map(rank_delta).fillna(0).astype(int)
    theme_counts["trend"]       = theme_counts["share_delta"].apply(
        lambda d: "↑" if d > 0.5 else ("↓" if d < -0.5 else "→")
    )
    for col in ["imdb_rating", "rt_score", "metacritic", "revenue_m"]:
        if col in exploded.columns:
            theme_counts[f"avg_{col}"] = (
                theme_counts["themes"].map(exploded.groupby("themes")[col].mean()).round(2)
            )
else:
    exploded = pd.DataFrame()
    theme_counts = pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 — MARKET CONTEXT
# ══════════════════════════════════════════════════════════════════════════
if page == "Market Context":

    # ── Setup ──────────────────────────────────────────────────────────────
    current_year  = date.today().year
    partial_years = [y for y in years if y >= current_year]
    full_years    = [y for y in years if y < current_year]

    def mark_partial(fig):
        if years:
            fig.update_xaxes(
                tickmode="array",
                tickvals=years,
                ticktext=[str(y) for y in years],
            )
        for yr in partial_years:
            fig.add_vrect(
                x0=yr - 0.45, x1=yr + 0.45,
                fillcolor="rgba(251,191,36,0.06)",
                line_color="rgba(251,191,36,0.3)",
                line_width=1, line_dash="dot",
            )
        return fig

    theatrical_df = df[df["revenue"] > 1_000_000].copy()
    has_bo        = not theatrical_df.empty
    yr_counts     = df.groupby("release_year").size()

    def _pct_chg(a, b):
        return (b - a) / a * 100 if a and a != 0 else None

    # ── Page header ────────────────────────────────────────────────────────
    active = [s for s in [
        selected_lang          if selected_lang          != "All" else None,
        selected_genre         if selected_genre         != "All" else None,
        selected_release_type  if selected_release_type  != "All" else None,
    ] if s]
    st.markdown(
        f'<div style="margin-bottom:1.5rem;">'
        f'<div style="font-size:1.45rem;font-weight:700;color:#0f172a;letter-spacing:-0.025em;">Market Context</div>'
        f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">'
        f'{len(df):,} films · {selected_years[0]}–{selected_years[1]}'
        + (f' · {" · ".join(active)}' if active else '') +
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Signal cards (executive summary) ──────────────────────────────────
    sig_data = []   # (badge_type, badge_text, body)

    if full_years and len(full_years) >= 2:
        last_full, prev_full = full_years[-1], full_years[-2]
        n_last = yr_counts.get(last_full, 0)
        n_prev = yr_counts.get(prev_full, 0)
        chg    = _pct_chg(n_prev, n_last)
        if chg is not None:
            sig_data.append((
                "up" if chg >= 0 else "down",
                "VOLUME",
                f"Release volume {'grew' if chg >= 0 else 'fell'} <strong>{abs(chg):.0f}%</strong> "
                f"from {prev_full} to {last_full} ({n_prev:,} → {n_last:,} films).",
            ))

        stream_by_yr = df.groupby("release_year").apply(
            lambda g: (g["release_type"] == "streaming_only").mean() * 100
        )
        s_last  = stream_by_yr.get(last_full)
        s_first = stream_by_yr.get(full_years[0])
        if s_last is not None and s_first is not None:
            s_chg = s_last - s_first
            sig_data.append((
                "up" if s_chg >= 0 else "neutral",
                "STRUCTURE",
                f"Streaming-only share {'rose' if s_chg >= 0 else 'fell'} from "
                f"<strong>{s_first:.0f}%</strong> ({full_years[0]}) to "
                f"<strong>{s_last:.0f}%</strong> ({last_full}).",
            ))

        if has_bo:
            bo_yr_s = theatrical_df.groupby("release_year")["revenue"].sum() / 1e9
            bo_l, bo_p = bo_yr_s.get(last_full), bo_yr_s.get(prev_full)
            if bo_l and bo_p:
                bo_chg = _pct_chg(bo_p, bo_l)
                sig_data.append((
                    "up" if bo_chg >= 0 else "down",
                    "BOX OFFICE",
                    f"Reported theatrical box office <strong>${bo_l:.1f}B</strong> in {last_full} "
                    f"({bo_chg:+.0f}% YoY). Streaming revenue not available.",
                ))

    if partial_years:
        sig_data.append((
            "caution", "DATA COVERAGE",
            f"{', '.join(str(y) for y in partial_years)} is incomplete — "
            f"collection still in progress. Treat as provisional.",
        ))

    # Render up to 4 signal cards in a row
    if sig_data:
        cols = st.columns(min(len(sig_data), 4))
        for col, (btype, btxt, body) in zip(cols, sig_data[:4]):
            with col:
                signal(btype, btxt, body)
        st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Provisional data note ──────────────────────────────────────────────
    if partial_years:
        st.markdown(
            f'<div style="font-size:0.72rem;color:#b45309;background:#fefce8;border:1px solid #fcd34d;'
            f'border-radius:6px;padding:8px 12px;margin-bottom:1rem;">'
            f'⚠ {", ".join(str(y) for y in partial_years)} data is incomplete — '
            f'collection still in progress. Treat time-series values for this year as provisional.</div>',
            unsafe_allow_html=True,
        )

    # ── Tier-1 KPIs ────────────────────────────────────────────────────────
    streaming_only = df[df["release_type"] == "streaming_only"]
    theatrical     = df[df["release_type"].isin(["theatrical", "theatrical_first"])]
    top_lang_name  = df["original_language"].value_counts().index[0].upper()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Total releases", f"{len(df):,}",
            f"{selected_years[0]}–{selected_years[1]}")
    with k2:
        if has_bo:
            kpi("Box office (reported)",
                f"${theatrical_df['revenue'].sum()/1e9:.1f}B",
                "theatrical only · streaming revenue n/a")
        else:
            kpi("Box office", "—", "no theatrical data in current filters")
    with k3:
        kpi("Streaming only",
            f"{len(streaming_only)/len(df)*100:.0f}%",
            f"{len(streaming_only):,} of {len(df):,} films")
    with k4:
        kpi("Original languages", df["original_language"].nunique(),
            f"dominant: {top_lang_name}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 1 — Release volume & structure
    # ══════════════════════════════════════════════════════════════════════
    section("Release volume & structure")
    col1, col2 = st.columns(2)

    with col1:
        chart_label("Films released per year")
        by_year = df.groupby(["release_year", "release_type_label"]).size().reset_index(name="count")
        fig_vol = px.bar(
            by_year, x="release_year", y="count", color="release_type_label",
            color_discrete_map=RELEASE_TYPE_COLORS,
            labels={"release_year": "", "count": "Films", "release_type_label": ""},
        )
        chart_style(fig_vol)
        fig_vol.update_layout(bargap=0.25, legend=dict(orientation="h", y=-0.15, x=0))
        mark_partial(fig_vol)
        st.plotly_chart(fig_vol, use_container_width=True)

    with col2:
        chart_label("Release type share — % of annual releases")
        pvt = df.groupby(["release_year", "release_type_label"]).size().unstack(fill_value=0)
        pvt_pct = (pvt.div(pvt.sum(axis=1), axis=0) * 100).reset_index().melt(
            id_vars="release_year", var_name="release_type_label", value_name="pct"
        )
        fig_share = px.bar(
            pvt_pct, x="release_year", y="pct", color="release_type_label",
            color_discrete_map=RELEASE_TYPE_COLORS, barmode="stack",
            labels={"release_year": "", "pct": "%", "release_type_label": ""},
            text=pvt_pct["pct"].apply(lambda x: f"{x:.0f}%" if x >= 9 else ""),
        )
        fig_share.update_traces(textposition="inside", textfont_size=9,
                                textfont_color="white")
        chart_style(fig_share, hgrid=False)
        fig_share.update_layout(bargap=0.25, legend=dict(orientation="h", y=-0.15, x=0))
        mark_partial(fig_share)
        st.plotly_chart(fig_share, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 2 — Market value
    # ══════════════════════════════════════════════════════════════════════
    section("Market value  ·  theatrical box office")
    st.markdown(
        '<span style="font-size:0.72rem;color:#94a3b8;">'
        'Streaming revenue is not publicly available. Box office = worldwide gross where reported — '
        'partial for many titles. Streaming-only films have no revenue.</span>',
        unsafe_allow_html=True,
    )

    if not has_bo:
        st.info("No theatrical revenue data in the current filter set.")
    else:
        bo1, bo2, bo3 = st.columns(3)

        with bo1:
            chart_label("Total box office by year ($B)")
            bo_yr = theatrical_df.groupby("release_year")["revenue"].sum().reset_index()
            bo_yr["bo_b"] = bo_yr["revenue"] / 1e9
            fig_bo = px.bar(
                bo_yr, x="release_year", y="bo_b",
                color_discrete_sequence=[ACCENT],
                labels={"release_year": "", "bo_b": "$B"},
                text=bo_yr["bo_b"].apply(lambda x: f"${x:.1f}B"),
            )
            fig_bo.update_traces(textposition="outside", textfont_size=10)
            chart_style(fig_bo, height=240)
            fig_bo.update_layout(bargap=0.3, showlegend=False)
            mark_partial(fig_bo)
            st.plotly_chart(fig_bo, use_container_width=True)

        with bo2:
            chart_label("Avg vs median revenue per theatrical film ($M)")
            bo_stats = (
                theatrical_df.groupby("release_year")["revenue"]
                .agg(avg="mean", med="median").reset_index()
            )
            bo_stats["avg_m"] = bo_stats["avg"] / 1e6
            bo_stats["med_m"] = bo_stats["med"] / 1e6
            fig_avg = go.Figure()
            fig_avg.add_trace(go.Scatter(
                x=bo_stats["release_year"], y=bo_stats["avg_m"],
                mode="lines+markers", name="Avg",
                line=dict(color=ACCENT, width=2),
                marker=dict(size=6),
            ))
            fig_avg.add_trace(go.Scatter(
                x=bo_stats["release_year"], y=bo_stats["med_m"],
                mode="lines+markers", name="Median",
                line=dict(color="#8b5cf6", width=2, dash="dot"),
                marker=dict(size=6),
            ))
            chart_style(fig_avg, height=240)
            fig_avg.update_layout(
                legend=dict(orientation="h", y=1.08, x=0),
                yaxis_title="$M",
            )
            if years:
                fig_avg.update_xaxes(
                    tickmode="array",
                    tickvals=years,
                    ticktext=[str(y) for y in years],
                    range=[years[0] - 0.5, years[-1] + 0.5],
                )
            for yr in partial_years:
                fig_avg.add_vrect(x0=yr-0.3, x1=yr+0.3,
                                  fillcolor="rgba(251,191,36,0.06)", line_width=0)
            st.plotly_chart(fig_avg, use_container_width=True)
            st.markdown(
                '<span style="font-size:0.70rem;color:#94a3b8;">'
                'Avg > median signals blockbuster concentration in that year.</span>',
                unsafe_allow_html=True,
            )

        with bo3:
            chart_label("Revenue concentration — top-10 films' share of annual box office")

            def _top10_share(g):
                s = g["revenue"].sum()
                return g.nlargest(10, "revenue")["revenue"].sum() / s * 100 if s > 0 else None

            conc = (
                theatrical_df.groupby("release_year")
                .apply(_top10_share)
                .reset_index(name="pct")
                .dropna()
            )
            fig_conc = px.line(
                conc, x="release_year", y="pct", markers=True,
                color_discrete_sequence=["#f59e0b"],
                labels={"release_year": "", "pct": "Top-10 share (%)"},
            )
            fig_conc.add_hline(y=conc["pct"].mean(), line_dash="dot",
                               line_color="#e2e8f0", line_width=1)
            chart_style(fig_conc, height=240)
            fig_conc.update_layout(yaxis=dict(range=[0, 100], ticksuffix="%"))
            if years:
                fig_conc.update_xaxes(
                    tickmode="array",
                    tickvals=years,
                    ticktext=[str(y) for y in years],
                    range=[years[0] - 0.5, years[-1] + 0.5],
                )
            for yr in partial_years:
                fig_conc.add_vrect(x0=yr-0.3, x1=yr+0.3,
                                   fillcolor="rgba(251,191,36,0.06)", line_width=0)
            st.plotly_chart(fig_conc, use_container_width=True)
            st.markdown(
                '<span style="font-size:0.70rem;color:#94a3b8;">'
                'Rising = revenue concentrating into fewer titles. Dashed line = period average.</span>',
                unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 3 — Streaming landscape
    # ══════════════════════════════════════════════════════════════════════
    section("Streaming landscape")
    st.markdown(
        '<span style="font-size:0.72rem;color:#94a3b8;">'
        'Platforms: TMDB watch providers, subscription flatrate, US. '
        'Days to streaming = TMDB digital release date (proxy).</span>',
        unsafe_allow_html=True,
    )

    streaming_df = df[df["streaming_platform"].notna()].copy()
    has_streaming = not streaming_df.empty

    if not has_streaming:
        st.info("No streaming platform data in the current filter set.")
    else:
        sp1, sp2, sp3 = st.columns(3)

        with sp1:
            chart_label("Platform distribution — films on each platform")
            plat_counts = (
                streaming_df["streaming_platform"].value_counts()
                .reset_index()
            )
            plat_counts.columns = ["platform", "count"]
            plat_counts["share"] = (plat_counts["count"] / len(streaming_df) * 100).round(1)
            plat_counts = plat_counts.sort_values("share")
            fig_plat = px.bar(
                plat_counts, x="share", y="platform", orientation="h",
                text=plat_counts["share"].apply(lambda x: f"{x:.0f}%"),
                color_discrete_sequence=[ACCENT],
                labels={"platform": "", "share": "% of streaming films"},
            )
            fig_plat.update_traces(textposition="outside")
            chart_style(fig_plat, height=220, hgrid=False)
            fig_plat.update_layout(margin=dict(l=0, r=50, t=20, b=0), showlegend=False)
            st.plotly_chart(fig_plat, use_container_width=True)

        with sp2:
            chart_label("Platform mix by year — share of streaming films")
            top_plats = (
                streaming_df["streaming_platform"].value_counts().head(6).index.tolist()
            )
            plat_yr = (
                streaming_df[streaming_df["streaming_platform"].isin(top_plats)]
                .groupby(["release_year", "streaming_platform"]).size()
                .reset_index(name="count")
            )
            plat_yr_total = streaming_df.groupby("release_year").size().rename("total")
            plat_yr = plat_yr.merge(plat_yr_total, on="release_year")
            plat_yr["share"] = plat_yr["count"] / plat_yr["total"] * 100
            fig_plat_yr = px.bar(
                plat_yr, x="release_year", y="share",
                color="streaming_platform",
                color_discrete_sequence=SERIES_COLORS,
                barmode="stack",
                labels={"release_year": "", "share": "%", "streaming_platform": ""},
            )
            chart_style(fig_plat_yr, height=220, hgrid=False)
            fig_plat_yr.update_layout(
                bargap=0.25,
                legend=dict(orientation="h", y=-0.15, x=0),
            )
            mark_partial(fig_plat_yr)
            st.plotly_chart(fig_plat_yr, use_container_width=True)

        with sp3:
            dts_df = df[df["days_to_streaming"].notna() & (df["days_to_streaming"] >= 0)].copy()
            if dts_df.empty:
                st.info("No days-to-streaming data available.")
            else:
                chart_label("Median days theatrical → streaming, by year")
                dts_yr = (
                    dts_df.groupby("release_year")["days_to_streaming"]
                    .median().reset_index(name="median_days")
                )
                fig_dts = px.bar(
                    dts_yr, x="release_year", y="median_days",
                    color_discrete_sequence=["#8b5cf6"],
                    labels={"release_year": "", "median_days": "Median days"},
                    text=dts_yr["median_days"].apply(lambda x: f"{x:.0f}d"),
                )
                fig_dts.update_traces(textposition="outside")
                chart_style(fig_dts, height=220)
                fig_dts.update_layout(bargap=0.3, showlegend=False)
                mark_partial(fig_dts)
                st.plotly_chart(fig_dts, use_container_width=True)
                st.markdown(
                    '<span style="font-size:0.70rem;color:#94a3b8;">'
                    'Falling = window between theatrical and streaming is shrinking.</span>',
                    unsafe_allow_html=True,
                )

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 4 — Content mix  (Language · Genre · Theme in parallel tabs)
    # ══════════════════════════════════════════════════════════════════════
    section("Content mix")
    st.markdown(
        '<span style="font-size:0.72rem;color:#94a3b8;">'
        'Original language = language of the original production (TMDB). '
        'Not release territory, dubbing, or localization. '
        'Genres and themes may be multi-valued per film.</span>',
        unsafe_allow_html=True,
    )

    tab_lang, tab_genre, tab_theme = st.tabs(["Original language", "Genre", "Theme"])

    total_by_yr = df.groupby("release_year").size().rename("total")

    with tab_lang:
        tl1, tl2 = st.columns(2)

        with tl1:
            chart_label("Top original languages — share of releases")
            lc = df["original_language"].value_counts().head(15).reset_index()
            lc.columns = ["language", "count"]
            lc["share"] = (lc["count"] / len(df) * 100).round(1)
            lc = lc.sort_values("share")
            fig_lc = px.bar(
                lc, x="share", y="language", orientation="h",
                text=lc["share"].apply(lambda x: f"{x:.1f}%"),
                color_discrete_sequence=[ACCENT],
                labels={"language": "", "share": "% of releases"},
            )
            fig_lc.update_traces(textposition="outside", marker_color=ACCENT,
                                 marker_opacity=lc["share"].rank(pct=True).clip(0.4, 1.0))
            chart_style(fig_lc, height=420, hgrid=False)
            fig_lc.update_layout(margin=dict(l=0, r=50, t=20, b=0))
            st.plotly_chart(fig_lc, use_container_width=True)

        with tl2:
            chart_label("Top-6 language share by year")
            top6_langs = df["original_language"].value_counts().head(6).index.tolist()
            lang_yr = (
                df[df["original_language"].isin(top6_langs)]
                .groupby(["release_year", "original_language"]).size()
                .reset_index(name="count")
                .merge(total_by_yr, on="release_year")
            )
            lang_yr["share"] = lang_yr["count"] / lang_yr["total"] * 100
            fig_lyr = px.bar(
                lang_yr, x="release_year", y="share",
                color="original_language",
                color_discrete_sequence=SERIES_COLORS,
                barmode="stack",
                labels={"release_year": "", "share": "%", "original_language": ""},
            )
            chart_style(fig_lyr, height=420, hgrid=False)
            fig_lyr.update_layout(
                bargap=0.25,
                legend=dict(orientation="h", y=-0.12, x=0),
            )
            mark_partial(fig_lyr)
            st.plotly_chart(fig_lyr, use_container_width=True)

    with tab_genre:
        tg1, tg2 = st.columns(2)

        with tg1:
            chart_label("Top genres — share of releases")
            gc = genre_exp_df["genre"].value_counts().head(15).reset_index()
            gc.columns = ["genre", "count"]
            gc["share"] = (gc["count"] / len(df) * 100).round(1)
            gc = gc.sort_values("share")
            fig_gc = px.bar(
                gc, x="share", y="genre", orientation="h",
                text=gc["share"].apply(lambda x: f"{x:.0f}%"),
                color_discrete_sequence=["#8b5cf6"],
                labels={"genre": "", "share": "% of releases"},
            )
            fig_gc.update_traces(textposition="outside")
            chart_style(fig_gc, height=420, hgrid=False)
            fig_gc.update_layout(margin=dict(l=0, r=50, t=20, b=0))
            st.plotly_chart(fig_gc, use_container_width=True)
            st.markdown(
                '<span style="font-size:0.70rem;color:#94a3b8;">'
                'Films can have multiple genres — values are not mutually exclusive.</span>',
                unsafe_allow_html=True,
            )

        with tg2:
            chart_label("Top-5 genre share over time — falling = diversification")
            top5_genres = genre_exp_df["genre"].value_counts().head(5).index.tolist()
            gen_rows = []
            for yr, tot in total_by_yr.items():
                yr_films = genre_exp_df[genre_exp_df["release_year"] == yr]
                for g in top5_genres:
                    n = yr_films[yr_films["genre"] == g]["id"].nunique()
                    gen_rows.append({"Year": yr, "Genre": g, "share": n / tot * 100})
            gen_conc = pd.DataFrame(gen_rows)
            fig_gc2 = px.line(
                gen_conc, x="Year", y="share", color="Genre",
                markers=True,
                color_discrete_sequence=SERIES_COLORS,
                labels={"share": "%", "Year": ""},
            )
            chart_style(fig_gc2, height=420)
            fig_gc2.update_layout(legend=dict(orientation="h", y=-0.12, x=0))
            fig_gc2.update_traces(line_width=2, marker_size=5)
            mark_partial(fig_gc2)
            st.plotly_chart(fig_gc2, use_container_width=True)

    with tab_theme:
        if not themes_available or theme_counts.empty:
            st.info(
                f"Theme extraction {coverage:.0f}% complete. "
                f"This view will update as more films are tagged."
            )
        else:
            tt1, tt2 = st.columns(2)

            with tt1:
                chart_label(f"Theme distribution — {total_tagged:,} films tagged ({coverage:.0f}% coverage)")
                top15 = theme_counts.head(15).copy()
                top15["Theme"] = top15["themes"].apply(fmt_theme)
                top15 = top15.sort_values("count")
                fig_tt = px.bar(
                    top15, x="count", y="Theme", orientation="h",
                    text=top15["share_pct"].apply(lambda x: f"{x:.1f}%"),
                    color_discrete_sequence=[ACCENT],
                    labels={"count": "Films", "Theme": ""},
                )
                fig_tt.update_traces(textposition="outside")
                chart_style(fig_tt, height=420, hgrid=False)
                fig_tt.update_layout(margin=dict(l=0, r=50, t=20, b=0))
                st.plotly_chart(fig_tt, use_container_width=True)

            with tt2:
                chart_label("Top-6 theme share by year — share of tagged films")
                top6_themes = theme_counts.head(6)["themes"].tolist()
                tagged_by_yr = df_with_themes.groupby("release_year").size().rename("total")
                theme_yr = (
                    exploded[exploded["themes"].isin(top6_themes)]
                    .groupby(["release_year", "themes"]).size()
                    .reset_index(name="count")
                    .merge(tagged_by_yr, on="release_year")
                )
                theme_yr["share"] = theme_yr["count"] / theme_yr["total"] * 100
                theme_yr["Theme"] = theme_yr["themes"].apply(fmt_theme)
                fig_tyr = px.bar(
                    theme_yr, x="release_year", y="share",
                    color="Theme",
                    color_discrete_sequence=SERIES_COLORS,
                    barmode="stack",
                    labels={"release_year": "", "share": "%", "Theme": ""},
                )
                chart_style(fig_tyr, height=420, hgrid=False)
                fig_tyr.update_layout(
                    bargap=0.25,
                    legend=dict(orientation="h", y=-0.12, x=0),
                )
                mark_partial(fig_tyr)
                st.plotly_chart(fig_tyr, use_container_width=True)
                st.markdown(
                    '<span style="font-size:0.70rem;color:#94a3b8;">'
                    'Theme × outcome analysis → Drivers tab.</span>',
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 — DRIVERS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Drivers":
    active = [s for s in [
        selected_lang          if selected_lang          != "All" else None,
        selected_genre         if selected_genre         != "All" else None,
        selected_release_type  if selected_release_type  != "All" else None,
    ] if s]
    st.markdown(
        f'<div style="margin-bottom:1.2rem;">'
        f'<div style="font-size:1.45rem;font-weight:700;color:#0f172a;letter-spacing:-0.025em;">Drivers</div>'
        f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">'
        f'{len(df):,} films · {selected_years[0]}–{selected_years[1]}'
        + (f' · {" · ".join(active)}' if active else '') +
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Outcome selector
    st.markdown("**Analyzing outcome:**")
    selected_outcome = st.radio(
        "Outcome",
        list(OUTCOME_COLS.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="outcome_key",
    )
    outcome_col = OUTCOME_COLS[selected_outcome]

    # Filter for outcome
    if outcome_col == "revenue_m":
        df_out = df[df["revenue_m"].notna() & (df["revenue"] > 1_000_000)].copy()
    else:
        df_out = df[df[outcome_col].notna()].copy() if outcome_col in df.columns else pd.DataFrame()

    # ── Insight summary ────────────────────────────────────────────────────
    if themes_available and not theme_counts.empty and f"avg_{outcome_col}" in theme_counts.columns:
        valid_themes = theme_counts.dropna(subset=[f"avg_{outcome_col}"])
        valid_themes_min5 = valid_themes[valid_themes["count"] >= 5]

        if not valid_themes_min5.empty:
            top_perf = valid_themes_min5.sort_values(f"avg_{outcome_col}", ascending=False).iloc[0]
            most_freq = theme_counts.iloc[0]
            median_out = (
                df_out[outcome_col].median()
                if not df_out.empty and outcome_col in df_out.columns
                else None
            )
            median_freq_val = valid_themes["count"].median()
            median_out_val = valid_themes[f"avg_{outcome_col}"].median()

            niche_themes = valid_themes_min5[
                (valid_themes_min5["count"] <= median_freq_val) &
                (valid_themes_min5[f"avg_{outcome_col}"] >= median_out_val)
            ].sort_values(f"avg_{outcome_col}", ascending=False)

            most_freq_avg = most_freq.get(f"avg_{outcome_col}")
            most_freq_str = fmt_outcome(most_freq_avg, outcome_col) if most_freq_avg is not None else "—"
            median_str = fmt_outcome(median_out, outcome_col) if median_out is not None else "—"
            above_below = "above" if (most_freq_avg is not None and median_out is not None and most_freq_avg >= median_out) else "below"

            parts = [
                f"On <b>{selected_outcome}</b>, the top-performing theme is "
                f"<b>{fmt_theme(top_perf['themes'])}</b> "
                f"(avg {fmt_outcome(top_perf[f'avg_{outcome_col}'], outcome_col)}, "
                f"{top_perf['count']:.0f} films).",
                f"The most frequent theme <b>{fmt_theme(most_freq['themes'])}</b> "
                f"scores {most_freq_str} — {above_below} the dataset median of {median_str}.",
            ]
            if not niche_themes.empty:
                nr = niche_themes.iloc[0]
                parts.append(
                    f"<b>{fmt_theme(nr['themes'])}</b> is low-frequency but above average "
                    f"on this outcome ({fmt_outcome(nr[f'avg_{outcome_col}'], outcome_col)})."
                )

            caveat = (
                "Trend = share of tagged releases, midpoint-split. Not raw count change."
            )
            st.markdown(
                f'<div class="insight-block">'
                f'{"  ".join(parts)}'
                f'<div class="insight-caveat">{caveat}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_theme, tab_genre, tab_lang, tab_release = st.tabs(
        ["By Theme", "By Genre", "By Language", "By Release window"]
    )

    # ── BY THEME ──────────────────────────────────────────────────────────
    with tab_theme:
        if not themes_available or theme_counts.empty:
            st.info("Theme extraction is still running. Theme analysis requires theme data.")
        elif f"avg_{outcome_col}" not in theme_counts.columns:
            st.info(f"No {selected_outcome} data available for theme analysis.")
        else:
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown(f"**Theme table — sorted by avg {selected_outcome}**")
                disp = theme_counts.copy()
                disp = disp.dropna(subset=[f"avg_{outcome_col}"])
                disp["Theme"] = disp["themes"].apply(fmt_theme)
                disp["Films"] = disp["count"]
                disp["Share %"] = disp["share_pct"]
                disp["Share trend (±pp)"] = disp["share_delta"].apply(
                    lambda d: f"+{d:.1f}pp" if d > 0 else f"{d:.1f}pp"
                )
                disp["Rank Δ"] = disp["rank_change"].apply(
                    lambda r: f"↑{r}" if r > 0 else (f"↓{abs(r)}" if r < 0 else "—")
                )
                disp[f"Avg {selected_outcome}"] = disp[f"avg_{outcome_col}"].apply(
                    lambda v: fmt_outcome(v, outcome_col)
                )
                disp = disp.sort_values(f"avg_{outcome_col}", ascending=False)
                show_cols = ["Theme", "Films", "Share %", "Share trend (±pp)", "Rank Δ", f"Avg {selected_outcome}"]
                st.dataframe(disp[show_cols], use_container_width=True, hide_index=True, height=440)

            with col_right:
                st.markdown(f"**Frequency × {selected_outcome} quadrant**")
                q_data = theme_counts.dropna(subset=[f"avg_{outcome_col}"]).copy()
                med_count = q_data["count"].median()
                med_outcome = q_data[f"avg_{outcome_col}"].median()

                q_data["quadrant"] = q_data.apply(
                    lambda r: (
                        "Proven ground"  if r["count"] > med_count and r[f"avg_{outcome_col}"] >= med_outcome
                        else "Crowded & weak" if r["count"] > med_count
                        else "Hidden gems"    if r[f"avg_{outcome_col}"] >= med_outcome
                        else "Low signal"
                    ),
                    axis=1,
                )

                fig_quad = px.scatter(
                    q_data,
                    x="count", y=f"avg_{outcome_col}",
                    text=q_data["themes"].apply(fmt_theme),
                    size="count",
                    color="quadrant",
                    color_discrete_map=QUAD_COLORS,
                    labels={
                        "count": "Number of films",
                        f"avg_{outcome_col}": f"Avg {selected_outcome}",
                        "quadrant": "",
                    },
                    size_max=42,
                    hover_data={"share_pct": True, "share_delta": True},
                )
                fig_quad.add_hline(y=med_outcome, line_dash="dot", line_color="#94a3b8", line_width=1)
                fig_quad.add_vline(x=med_count,   line_dash="dot", line_color="#94a3b8", line_width=1)
                fig_quad.update_traces(textposition="top center", textfont_size=10)
                chart_style(fig_quad, height=420)
                fig_quad.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
                )
                st.plotly_chart(fig_quad, use_container_width=True)

            # Theme detail panel
            section("Theme detail")
            raw_to_title = {t: fmt_theme(t) for t in theme_counts["themes"]}
            title_to_raw = {v: k for k, v in raw_to_title.items()}

            selected_display = st.selectbox(
                "Explore a theme →",
                ["—"] + list(raw_to_title.values()),
                label_visibility="collapsed",
                key="theme_detail_drivers",
            )

            if selected_display != "—":
                theme_raw = title_to_raw[selected_display]
                theme_films = exploded[exploded["themes"] == theme_raw].drop_duplicates("id")
                theme_row = theme_counts[theme_counts["themes"] == theme_raw].iloc[0]
                glossary = THEME_GLOSSARY.get(theme_raw, {})

                defn = glossary.get("definition", "No definition available for this theme.")
                kw_list = glossary.get("keywords", [])
                kw_html = (
                    f'<div class="theme-keywords">Keywords: {" · ".join(kw_list)}</div>'
                    if kw_list else ""
                )
                st.markdown(
                    f'<div class="theme-definition-box">'
                    f'<strong>{selected_display}</strong><br/>{defn}'
                    f'{kw_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    kpi("Films", theme_row["count"])
                with d2:
                    kpi("Share %", f"{theme_row['share_pct']}%", "of tagged releases")
                with d3:
                    avg_val = theme_row.get(f"avg_{outcome_col}")
                    kpi(f"Avg {selected_outcome}", fmt_outcome(avg_val, outcome_col))
                with d4:
                    sd = theme_row["share_delta"]
                    sign = "+" if sd > 0 else ""
                    kpi("Share trend", f"{sign}{sd:.1f}pp", "vs. prior half")

                st.markdown(f"**Top films by {selected_outcome}**")
                if outcome_col in theme_films.columns:
                    rep_films = (
                        theme_films[theme_films[outcome_col].notna()]
                        [["title", "release_year", "director", "original_language", outcome_col, "release_type_label"]]
                        .sort_values(outcome_col, ascending=False)
                        .head(8)
                    )
                    st.dataframe(rep_films, use_container_width=True, hide_index=True)

                film_ids = theme_films["id"].unique()
                co_themes = (
                    exploded[
                        exploded["id"].isin(film_ids) & (exploded["themes"] != theme_raw)
                    ]["themes"]
                    .value_counts()
                    .head(6)
                )
                if not co_themes.empty:
                    st.markdown("**Co-occurring themes**")
                    co_df = co_themes.reset_index()
                    co_df.columns = ["Theme", "Co-occurrences"]
                    co_df["Theme"] = co_df["Theme"].apply(fmt_theme)
                    st.dataframe(co_df, use_container_width=True, hide_index=True)

                st.markdown("**Volume and share by year**")
                theme_by_yr = theme_films.groupby("release_year").size().reset_index(name="films")
                total_by_yr = df_with_themes.groupby("release_year").size().reset_index(name="total")
                theme_by_yr = theme_by_yr.merge(total_by_yr, on="release_year", how="left")
                theme_by_yr["share"] = (theme_by_yr["films"] / theme_by_yr["total"] * 100).round(1)

                yt1, yt2 = st.columns(2)
                with yt1:
                    fig_vol = px.bar(
                        theme_by_yr, x="release_year", y="films",
                        color_discrete_sequence=[ACCENT],
                        labels={"release_year": "Year", "films": "Films"},
                        text="films",
                    )
                    fig_vol.update_traces(textposition="outside")
                    chart_style(fig_vol, height=200)
                    fig_vol.update_layout(
                        showlegend=False, bargap=0.3,
                        yaxis=dict(tickformat="d"),
                    )
                    st.plotly_chart(fig_vol, use_container_width=True)

                with yt2:
                    fig_share = px.line(
                        theme_by_yr, x="release_year", y="share",
                        markers=True,
                        color_discrete_sequence=[ACCENT],
                        labels={"release_year": "Year", "share": "Share of releases (%)"},
                    )
                    chart_style(fig_share, height=200)
                    fig_share.update_layout(showlegend=False)
                    st.plotly_chart(fig_share, use_container_width=True)

    # ── BY GENRE ──────────────────────────────────────────────────────────
    with tab_genre:
        if df_out.empty or outcome_col not in df_out.columns:
            st.info(f"No {selected_outcome} data available.")
        else:
            genre_out = (
                df_out.assign(genre=df_out["genres"].str.split(", "))
                .explode("genre")
                .dropna(subset=["genre", outcome_col])
            )
            genre_stats = (
                genre_out.groupby("genre")[outcome_col]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={"mean": "avg_outcome", "count": "films"})
                .query("films >= 5")
                .sort_values("avg_outcome", ascending=False)
            )

            genre_stats["label"] = genre_stats["avg_outcome"].apply(
                lambda v: fmt_outcome(v, outcome_col)
            )

            fig_genre = px.bar(
                genre_stats.sort_values("avg_outcome"),
                x="avg_outcome", y="genre", orientation="h",
                text="label",
                color_discrete_sequence=[ACCENT],
                labels={"avg_outcome": f"Avg {selected_outcome}", "genre": ""},
            )
            fig_genre.update_traces(textposition="outside")
            chart_style(fig_genre, height=max(300, len(genre_stats) * 28), hgrid=False)
            fig_genre.update_layout(
                showlegend=False,
                margin=dict(l=0, r=50, t=20, b=0),
            )
            st.plotly_chart(fig_genre, use_container_width=True)

            genre_table = genre_stats[["genre", "films", "avg_outcome"]].copy()
            genre_table.columns = ["Genre", "Films", f"Avg {selected_outcome}"]
            genre_table[f"Avg {selected_outcome}"] = genre_stats["avg_outcome"].apply(
                lambda v: fmt_outcome(v, outcome_col)
            )

            total_genre = genre_out["genre"].value_counts().rename("total_films").reset_index()
            total_genre.columns = ["Genre", "Share Films"]
            genre_table = genre_table.merge(total_genre, on="Genre", how="left")
            genre_table["Share %"] = (genre_table["Share Films"] / len(df) * 100).round(1)
            st.dataframe(
                genre_table[["Genre", "Films", "Share %", f"Avg {selected_outcome}"]],
                use_container_width=True,
                hide_index=True,
            )

    # ── BY LANGUAGE ───────────────────────────────────────────────────────
    with tab_lang:
        if df_out.empty or outcome_col not in df_out.columns:
            st.info(f"No {selected_outcome} data available.")
        else:
            lang_stats = (
                df_out.groupby("original_language")[outcome_col]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={"mean": "avg_outcome", "count": "films", "original_language": "language"})
                .query("films >= 5")
                .sort_values("avg_outcome", ascending=False)
                .head(15)
            )
            lang_stats["label"] = lang_stats["avg_outcome"].apply(
                lambda v: fmt_outcome(v, outcome_col)
            )

            fig_lang = px.bar(
                lang_stats.sort_values("avg_outcome"),
                x="avg_outcome", y="language", orientation="h",
                text="label",
                color_discrete_sequence=[ACCENT],
                labels={"avg_outcome": f"Avg {selected_outcome}", "language": ""},
            )
            fig_lang.update_traces(textposition="outside")
            chart_style(fig_lang, height=max(300, len(lang_stats) * 28), hgrid=False)
            fig_lang.update_layout(
                showlegend=False,
                margin=dict(l=0, r=50, t=20, b=0),
            )
            st.plotly_chart(fig_lang, use_container_width=True)

            lang_table = lang_stats[["language", "films", "avg_outcome"]].copy()
            lang_table.columns = ["Language", "Films", f"Avg {selected_outcome}"]
            lang_table[f"Avg {selected_outcome}"] = lang_stats["avg_outcome"].apply(
                lambda v: fmt_outcome(v, outcome_col)
            )
            st.dataframe(lang_table, use_container_width=True, hide_index=True)

    # ── BY RELEASE WINDOW ─────────────────────────────────────────────────
    with tab_release:
        if df_out.empty or outcome_col not in df_out.columns:
            st.info(f"No {selected_outcome} data available.")
        else:
            rt_stats = (
                df_out.groupby("release_type_label")[outcome_col]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={"mean": "avg_outcome", "count": "films", "release_type_label": "release_type"})
                .sort_values("avg_outcome", ascending=False)
            )
            rt_stats["label"] = rt_stats["avg_outcome"].apply(
                lambda v: fmt_outcome(v, outcome_col)
            )

            fig_rt = px.bar(
                rt_stats,
                x="release_type", y="avg_outcome",
                text="label",
                color="release_type",
                color_discrete_map=RELEASE_TYPE_COLORS,
                labels={"release_type": "Release window", "avg_outcome": f"Avg {selected_outcome}"},
                custom_data=["films"],
            )
            fig_rt.update_traces(
                textposition="outside",
                hovertemplate="%{x}<br>Avg: %{y}<br>Films: %{customdata[0]}<extra></extra>",
            )
            chart_style(fig_rt)
            fig_rt.update_layout(showlegend=False)
            st.plotly_chart(fig_rt, use_container_width=True)

            rt_table = rt_stats[["release_type", "films", "avg_outcome"]].copy()
            rt_table.columns = ["Release window", "Films", f"Avg {selected_outcome}"]
            rt_table[f"Avg {selected_outcome}"] = rt_stats["avg_outcome"].apply(
                lambda v: fmt_outcome(v, outcome_col)
            )
            st.dataframe(rt_table, use_container_width=True, hide_index=True)

            if "days_to_streaming" in df_out.columns and df_out["days_to_streaming"].notna().any():
                st.markdown(f"**Days to streaming vs. {selected_outcome}**")
                scatter_dts = df_out[
                    df_out["days_to_streaming"].notna() & df_out[outcome_col].notna()
                ].copy()
                fig_dts = px.scatter(
                    scatter_dts,
                    x="days_to_streaming", y=outcome_col,
                    color="release_type_label",
                    color_discrete_map=RELEASE_TYPE_COLORS,
                    hover_name="title",
                    opacity=0.65,
                    labels={
                        "days_to_streaming": "Days to streaming",
                        outcome_col: f"Avg {selected_outcome}",
                        "release_type_label": "Release type",
                    },
                )
                chart_style(fig_dts)
                st.plotly_chart(fig_dts, use_container_width=True)
                st.caption("days_to_streaming uses TMDB digital release date as proxy.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE 3 — OPPORTUNITIES
# ══════════════════════════════════════════════════════════════════════════
elif page == "Opportunities":
    active = [s for s in [
        selected_lang          if selected_lang          != "All" else None,
        selected_genre         if selected_genre         != "All" else None,
        selected_release_type  if selected_release_type  != "All" else None,
    ] if s]
    st.markdown(
        f'<div style="margin-bottom:1.2rem;">'
        f'<div style="font-size:1.45rem;font-weight:700;color:#0f172a;letter-spacing:-0.025em;">Opportunities</div>'
        f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">'
        f'{len(df):,} films · {selected_years[0]}–{selected_years[1]}'
        + (f' · {" · ".join(active)}' if active else '') +
        f'</div></div>',
        unsafe_allow_html=True,
    )

    selected_outcome = st.radio(
        "Outcome",
        list(OUTCOME_COLS.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="outcome_key",
    )
    outcome_col = OUTCOME_COLS[selected_outcome]

    if not themes_available or theme_counts.empty:
        st.info("Theme extraction is still running. Opportunities analysis requires theme data.")
        st.stop()

    if f"avg_{outcome_col}" not in theme_counts.columns:
        st.info(f"No {selected_outcome} data available for opportunities analysis.")
        st.stop()

    valid = theme_counts.dropna(subset=[f"avg_{outcome_col}"])
    median_freq = valid["count"].median()
    median_outcome = valid[f"avg_{outcome_col}"].median()

    def theme_opp_table(filtered_df, cols):
        display = filtered_df.copy()
        display["Theme"] = display["themes"].apply(fmt_theme)
        display["Films"] = display["count"]
        display["Share %"] = display["share_pct"]
        display["Share trend (+pp)"] = display["share_delta"].apply(
            lambda d: f"+{d:.1f}pp" if d > 0 else f"{d:.1f}pp"
        )
        display[f"Avg {selected_outcome}"] = display[f"avg_{outcome_col}"].apply(
            lambda v: fmt_outcome(v, outcome_col)
        )
        display["Rank Δ"] = display["rank_change"].apply(
            lambda r: f"↑{r}" if r > 0 else (f"↓{abs(r)}" if r < 0 else "—")
        )
        show = [c for c in cols if c in display.columns]
        st.dataframe(display[show], use_container_width=True, hide_index=True)

    # ── Crowded & weak ─────────────────────────────────────────────────────
    section("Crowded & weak")
    st.caption(f"High-frequency themes scoring below median on {selected_outcome}. High competition, limited payoff.")

    crowded_weak = valid[
        (valid["count"] > median_freq) &
        (valid[f"avg_{outcome_col}"] < median_outcome)
    ].sort_values("count", ascending=False)

    if crowded_weak.empty:
        st.info("No crowded-weak themes in current filter set.")
    else:
        theme_opp_table(
            crowded_weak,
            ["Theme", "Films", "Share %", f"Avg {selected_outcome}", "Share trend (+pp)"],
        )

    # ── Growing niches ─────────────────────────────────────────────────────
    section("Growing niches")
    st.caption(
        f"Themes gaining share in the second half of the period AND scoring above median on {selected_outcome}."
    )

    growing = valid[
        (valid["share_delta"] > 0) &
        (valid[f"avg_{outcome_col}"] >= median_outcome) &
        (valid["count"] >= 3)
    ].sort_values("share_delta", ascending=False)

    if growing.empty:
        st.info("No growing niche themes in current filter set.")
    else:
        theme_opp_table(
            growing,
            ["Theme", "Films", "Share %", "Share trend (+pp)", f"Avg {selected_outcome}"],
        )

    # ── Hidden gems ────────────────────────────────────────────────────────
    section("Hidden gems")
    st.caption(
        f"Low-frequency themes with above-median performance on {selected_outcome}. "
        "Potentially underexplored territory."
    )

    hidden = valid[
        (valid["count"] <= median_freq) &
        (valid[f"avg_{outcome_col}"] >= median_outcome) &
        (valid["count"] >= 3)
    ].sort_values(f"avg_{outcome_col}", ascending=False)

    if hidden.empty:
        st.info("No hidden gem themes in current filter set.")
    else:
        theme_opp_table(
            hidden,
            ["Theme", "Films", "Share %", f"Avg {selected_outcome}", "Rank Δ"],
        )

    # ── Underserved combinations ───────────────────────────────────────────
    section("Underserved combinations")
    threshold = 20
    st.caption(
        f"Theme × genre pairs with above-median {selected_outcome} and fewer than {threshold} films. "
        "Cross-attribute gaps worth investigating."
    )

    if not exploded.empty and outcome_col in exploded.columns:
        combo = (
            exploded.copy()
            .assign(genre=lambda d: d["genres"].str.split(", "))
            .explode("genre")
            .dropna(subset=["genre"])
        )
        combo_stats = (
            combo.groupby(["themes", "genre"])
            .agg(films=("id", "nunique"), avg_outcome=(outcome_col, "mean"))
            .reset_index()
            .query(f"films >= 3 and films <= {threshold}")
            .dropna(subset=["avg_outcome"])
        )
        combo_stats = combo_stats[combo_stats["avg_outcome"] >= median_outcome]
        combo_stats = combo_stats.sort_values("avg_outcome", ascending=False)
        combo_stats["Theme"] = combo_stats["themes"].apply(fmt_theme)
        combo_stats["Genre"] = combo_stats["genre"]
        combo_stats["Films"] = combo_stats["films"]
        combo_stats[f"Avg {selected_outcome}"] = combo_stats["avg_outcome"].apply(
            lambda v: fmt_outcome(v, outcome_col)
        )

        if combo_stats.empty:
            st.info("No underserved combinations in current filter set.")
        else:
            st.dataframe(
                combo_stats[["Theme", "Genre", "Films", f"Avg {selected_outcome}"]],
                use_container_width=True,
                hide_index=True,
            )
        st.caption(
            f"Films ≤ {threshold} and above-median {selected_outcome}. "
            "These are structural gaps, not predictions."
        )
    else:
        st.info("Outcome data not available for combination analysis.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE 4 — METHODOLOGY
# ══════════════════════════════════════════════════════════════════════════
elif page == "Methodology":
    st.markdown(
        '<div style="margin-bottom:1.5rem;">'
        '<div style="font-size:1.45rem;font-weight:700;color:#0f172a;letter-spacing:-0.025em;">Methodology</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("""
### Analytical structure

ScreenTrend is organized around a separation between **attributes** and **outcomes**:

- **Attributes** (explanatory variables): theme, genre, language, release window, cast, director
- **Outcomes** (measured results): IMDB rating, Rotten Tomatoes score, Metacritic score, box office revenue

**Market Context** shows the distribution of attributes over time — how the content mix is structured.
**Drivers** explores how each attribute relates to a selected outcome.
**Opportunities** synthesizes those patterns into named spaces worth investigating.

This product identifies associations in observed data. It does not establish causality.

### Trend methodology
Theme trends on this platform are measured as **share of total tagged releases** in each
sub-period — not raw film counts. This controls for overall volume changes and the fact
that later years may have fewer films in the dataset due to collection timing.

A theme showing a negative raw count trend while releases are growing overall
is actually losing share — the share-adjusted view makes this distinction explicit.

---

**ScreenTrend** analyzes 2,302 films from 2020–2026 to surface structural patterns across
release type, language, genre, and AI-derived theme — as they relate to commercial, critical,
and awards outcomes.

---

### Data sources
| Source | Used for |
|---|---|
| Kaggle TMDB dataset (alanvourch) | Core metadata, revenue, cast, director |
| TMDB API | Watch providers, digital release dates |
| OMDb API | Rotten Tomatoes + Metacritic scores |
| Movie of the Night / RapidAPI | Subscription streaming dates |
| OpenAI GPT-4o-mini | Theme extraction from plot overviews |

### Release type classification
| Label | Logic |
|---|---|
| Theatrical only | Revenue > $1M, no streaming platform found |
| Theatrical → Streaming | Revenue > $1M, later on subscription streaming |
| Streaming only | Revenue = 0, available on subscription platform |
| Unknown | Insufficient data to classify |

### Theme extraction
Each film is tagged with 1–3 themes from a fixed 15-label taxonomy, using GPT-4o-mini applied
to TMDB plot overviews. Tags include a model confidence score.
Theme labels are machine-generated and depend on overview quality — they carry uncertainty.

### What this product does and does not do
This tool identifies **associations** and structural patterns. It does not establish
causal relationships. Correlation between theme recurrence and IMDB score reflects
observed co-occurrence in this dataset, not evidence that the theme drives quality.

### Known limitations
- 2020–2026 is a short window; long-cycle patterns are not detectable
- Box office data is missing for most streaming-only films
- Awards enrichment is not yet loaded
- `days_to_streaming` uses TMDB digital release date (buy/rent) as a proxy — not subscription date
- Release type classification uses revenue + current platform presence, not original distribution contracts
- Theme tags carry model uncertainty; overviews vary in detail and accuracy
    """)
