# ScreenTrend

A decision-support prototype that analyzes 2020–2026 films to understand how release type, talent, language, genre, and AI-derived themes relate to commercial success, critical reception, and awards recognition.

Built as a senior product manager portfolio project — demonstrating structured problem decomposition, metric design, LLM-based classification, and data pipeline engineering.

---

## What it does

ScreenTrend answers questions like:

- Which themes are most recurrent in a given period — and are some becoming crowded?
- Do streaming-only films perform differently on critic scores than theatrical releases?
- Which genres consistently outperform on IMDB rating vs. box office?
- Are certain themes associated with stronger critical reception when combined with specific genres or languages?

It does **not** predict hits. It identifies patterns, correlations, and structural observations across a broad dataset of notable films.

---

## Product pages

### Theme Intelligence *(MVP)*
- LLM-extracted themes from TMDB plot overviews using GPT-4o-mini
- Theme recurrence ranking and frequency over time
- Quarterly density heatmap — shows when themes cluster
- Theme vs. IMDB rating scatter
- Film browser by theme

### Market Overview
- Release volume by year, broken down by release type
- Release type share over time (streaming-only growth trend)
- Language and genre breakdowns
- Streaming platform distribution

### Success Explorer
- Filter by genre, release type, and minimum rating
- IMDB rating and box office distributions
- Genre vs. average rating
- Rating vs. revenue scatter

---

## Data sources

| Source | Used for | Cost |
|---|---|---|
| [Kaggle TMDB dataset](https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates) | Metadata, revenue, cast, director, overviews | Free |
| [TMDB API](https://www.themoviedb.org/documentation/api) | Watch providers, digital release dates | Free |
| [IMDB Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/) | Ratings, vote counts | Free |
| [OMDb API](https://www.omdbapi.com) | Rotten Tomatoes + Metacritic scores | Free (1K/day) |
| [Streaming Availability API](https://www.movieofthenight.com/about/api) | Platform streaming dates | Free (100/day) |
| OpenAI GPT-4o-mini | Theme extraction from plot overviews | ~$0.40 total |

**Total data cost: ~$0.40** (one-time LLM extraction).

---

## Dataset

- **2,302 films** — 2020 to 2026
- Inclusion threshold: TMDB vote count ≥ 200, has plot overview
- Languages: 30+ including English, French, Spanish, Korean, Japanese
- Release types: streaming-only (40%), theatrical-first (23%), theatrical (19%), unknown (18%)

---

## Architecture

```
data/raw/               ← Kaggle bulk downloads (not committed, ~600MB)
data/processed/         ← Filtered CSVs + daily job progress files
pipeline/
  ingest.py             ← Filter and clean Kaggle dataset
  db.py                 ← Supabase client + load helpers
  theme_extraction.py   ← GPT-4o-mini theme tagging pipeline
  watch_providers.py    ← TMDB watch providers + digital release dates
  omdb_scores.py        ← RT + Metacritic via OMDb (daily, 1K/day)
  streaming_dates.py    ← Platform streaming dates via Movie of the Night (daily, 100/day)
  run_pipeline.py       ← Master runner
app/
  main.py               ← Streamlit app
.github/workflows/
  daily_omdb_fetch.yml        ← GitHub Action: runs daily at 8am UTC
  daily_streaming_fetch.yml   ← GitHub Action: runs daily at 7am UTC
```

**Backend:** Supabase (Postgres)
**App:** Streamlit + Plotly
**LLM:** OpenAI GPT-4o-mini

---

## Theme taxonomy

Themes are extracted from TMDB plot overviews using GPT-4o-mini. Each film receives 1–3 tags from a defined taxonomy:

`class conflict / critique of elites` · `revenge` · `grief and loss` · `family conflict` · `coming of age` · `survival` · `technology / AI` · `social satire` · `romance across difference` · `justice / corruption` · `war / trauma` · `identity / belonging` · `power and control` · `redemption` · `isolation`

Theme tags are model-generated and carry uncertainty. Confidence scores are stored per tag.

---

## Running locally

### Prerequisites
- Python 3.9+
- Supabase project
- API keys: TMDB, OMDb, OpenAI, RapidAPI, Kaggle

### Setup

```bash
git clone https://github.com/Valeriovdb/ScreenTrend.git
cd ScreenTrend
pip install -r requirements.txt
cp .env.example .env
# fill in your API keys in .env
```

### Run the pipeline

```bash
# 1. Filter and clean the dataset (requires Kaggle download first)
python3 -m pipeline.run_pipeline --step ingest

# 2. Load into Supabase
python3 -m pipeline.run_pipeline --step load

# 3. Extract themes (OpenAI, ~$0.40, ~15 min)
python3 -m pipeline.run_pipeline --step themes

# 4. Fetch watch providers + digital release dates (TMDB)
python3 -m pipeline.watch_providers

# 5. Start enriching RT/Metacritic scores (1,000/day, runs via GitHub Actions)
python3 -m pipeline.omdb_scores

# 6. Start enriching streaming dates (100/day, runs via GitHub Actions)
python3 -m pipeline.streaming_dates
```

### Launch the app

```bash
streamlit run app/main.py
```

---

## Automated daily enrichment

Two GitHub Actions workflows run daily to progressively enrich the dataset:

| Workflow | Schedule | What it does |
|---|---|---|
| `daily_omdb_fetch.yml` | 8am UTC | Fetches RT + Metacritic for 1,000 films/day |
| `daily_streaming_fetch.yml` | 7am UTC | Fetches platform streaming dates for 100 films/day |

Progress is tracked in `data/processed/` and committed back to the repo after each run.

Required GitHub Secrets: `SUPABASE_URL`, `SUPABASE_KEY`, `OMDB_API_KEY`, `RAPIDAPI_KEY`

---

## Limitations

- **2020–2026 is a limited window** — sufficient for trend observation, not long-cycle pattern detection
- **Box office data is incomplete** — streaming-only films have no revenue; worldwide figures are often partial
- **Theme tags are model-generated** — carry uncertainty; depend on overview quality
- **Awards data not yet loaded** — planned enrichment
- **days_to_streaming** uses TMDB digital release date (buy/rent) as a proxy, not subscription streaming date
- **Release type classification** is based on revenue + current watch provider data, not original distribution contracts
- This product identifies associations, not causal relationships

---

## Portfolio context

This project demonstrates:

- **Structured problem decomposition** — breaking "what makes a film successful?" into separable, measurable lenses
- **Metric design** — defining commercial, critical, and awards success independently before any aggregation
- **LLM applied to classification** — GPT-4o-mini for structured theme extraction from unstructured text; the same pattern applies to interview analysis, customer feedback tagging, and content classification
- **Data pipeline engineering** — multi-source ingestion, incremental enrichment, automated daily jobs via GitHub Actions
- **Data realism** — deliberate tradeoffs about inclusion thresholds, missing fields, and proxy variables; limitations documented explicitly
