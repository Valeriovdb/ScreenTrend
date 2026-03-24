# ScreenTrend — project brief

## What this project is

**ScreenTrend** is a productized analytics prototype for the film industry.

Its goal is to help analysts, content investors, and industry observers understand how **movie attributes** and **market patterns** relate to different definitions of success.

This is **not** meant to predict the next hit.
It is meant to identify **patterns, correlations, and structural observations** across a broad set of films — descriptive and diagnostic, not predictive.

The analysis covers **movies released from 2020 to 2026**.

---

## Dataset scope and inclusion threshold

To keep the dataset analytically meaningful, only films meeting the following criteria are included:

- Listed on TMDB with **≥ 500 user votes**
- Has a TMDB overview (plot summary) available

This threshold filters out micro-budget and obscure titles while capturing notable theatrical releases, platform originals, and films with meaningful critical or awards presence.

Expected dataset size: approximately **2,500–4,000 films** across 2020–2026.

---

## Data sources

**Total data cost: $0**

All data sources used in this project are either free bulk downloads or free API tiers.

### Source 1: Kaggle — TMDB Movies Dataset (primary)
- URL: kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies
- Type: **bulk download**, updated daily, no API calls required
- Fields used: title, release date, original language, genres, runtime, revenue, vote average, vote count, overview (plot summary), keywords, IMDB ID
- Coverage: ~1M titles; filtered to ≥ 500 votes and 2020–2026 release years
- Limitation: snapshot may lag for very recent 2025–2026 films; TMDB API fills this gap

### Source 2: IMDB Non-Commercial Datasets (cast, crew, ratings)
- URL: datasets.imdb.com
- Type: **bulk download**, refreshed daily, free for non-commercial use
- Files used:
  - `title.basics` — title type, genres, runtime, release year
  - `title.ratings` — IMDB user rating and vote count
  - `title.principals` — cast and key crew (actor, director categories)
  - `name.basics` — person names linked to principals
- Joined to TMDB data via IMDB ID
- Limitation: no plot descriptions, no box office, no awards data

### Source 3: TMDB API (streaming providers + 2025–2026 gap fill)
- Type: **free API**, 50 requests/second, no paid tier required
- Used for:
  - Watch providers (streaming availability by platform and region) via `/movie/{id}/watch/providers`
  - Filling in films released in 2025–2026 not yet captured in the Kaggle snapshot
- Attribution required: data sourced from TMDB

### Source 4: OMDb API (critic scores)
- Type: **free tier**, 1,000 requests/day
- Used for:
  - Rotten Tomatoes critic score
  - Metacritic score
- At 1,000 requests/day, fetching scores for ~4,000 films takes approximately 4 days — acceptable for a one-time data build
- Limitation: does not include structured awards data despite what the free tier documentation implies

### Awards data: manual enrichment
Major awards (Oscars, BAFTA, Golden Globes, Cannes Palme d'Or, Berlin Golden Bear, Venice Golden Lion, Sundance Grand Jury Prize, Independent Spirit Awards) are not available via any free programmatic source in structured form.

These will be compiled as a manually curated lookup table — a one-time effort covering the major annual cycles from 2020 to 2026. Given the small number of annual award events, this is tractable.

This is acknowledged as a data gap for smaller festivals and technical categories.

---

## Release type taxonomy

A core structural variable in this dataset is **how a film was released**.

Four release types:

| Type | Definition |
|---|---|
| **Theatrical only** | Released in cinemas, no streaming window in dataset period |
| **Streaming only** | Released directly on a streaming platform, no theatrical window |
| **Concurrent** | Released simultaneously in cinemas and on a streaming platform |
| **Theatrical first, then streaming** | Released in cinemas, later made available on streaming |

This taxonomy enables analysis of:
- Volume of releases by type per year
- Whether critical, commercial, or awards outcomes differ by release type
- How streaming's share of notable releases has shifted from 2020 to 2026

---

## Core product thesis

Movie success is **multi-dimensional**.

The attributes associated with:
- **commercial success**
- **critical success**
- **awards success**

are not the same, and should not be collapsed into a single score.

The product helps users explore which combinations of genre, language, cast, release timing, themes, and narrative patterns are associated with stronger outcomes — depending on the kind of success they care about.

---

## Main user

**Independent analyst, content investor, or industry observer**

This is someone who wants to understand the film landscape without access to expensive proprietary tools (Comscore, EntTelligence, studio greenlight data).

They want to:
- understand what kinds of films are being released and in what volumes
- identify which themes and genres are crowded or trending
- explore what correlates with strong box office, critical reception, or awards
- see how streaming-only films compare to theatrical releases across success modes
- find structural patterns they can reason about for investment or editorial purposes

Secondary users:
- journalists and film critics looking for data-backed editorial angles
- producers and development executives without access to paid analytics

---

## Main product question

**Across 2020–2026 films, which combinations of movie attributes, release type, and AI-derived themes are associated with stronger commercial, critical, or awards outcomes?**

---

## Success modes

The product treats success as 3 separate lenses. Do not collapse them.

### 1. Commercial success
Signals:
- worldwide box office (from TMDB revenue field)
- opening weekend if available
- note: no ROI or budget-adjusted efficiency — budget data is too unreliable in public datasets to be analytically sound

### 2. Critical success
Signals:
- Rotten Tomatoes critic score (via OMDb)
- Metacritic score (via OMDb)
- IMDB user rating as supplementary audience signal
- festival recognition (Cannes, Berlin, Venice, Sundance, BAFTA, etc.)

### 3. Awards success
Signals:
- Oscar nominations and wins
- BAFTA nominations and wins
- Golden Globe nominations and wins
- Major international festival awards: Palme d'Or, Golden Bear, Golden Lion, Grand Jury prizes
- Independent Spirit Awards
- Total nominations count and wins count as derived metrics

Awards coverage is richer with festivals included. Even so, awards data is inherently sparse — it should be treated as a signal layer, not a primary outcome variable.

---

## Input variables

### A. Movie attributes
- title
- release date
- original language
- genre(s)
- cast (top-billed actors)
- director
- runtime
- franchise / sequel / remake / original (where available)
- IMDB plot description

### B. Release context
- release type (streaming only / theatrical only / concurrent / theatrical-first)
- release month and quarter
- streaming platform (if applicable)
- theatrical-to-streaming delay (for theatrical-first films)
- distributor / studio (where available)

### C. Outcome variables
- box office (commercial)
- critic score, audience score (critical)
- awards nominations and wins, festival recognition (awards)

---

## Theme and plot analysis

This is the core of the MVP and the primary differentiator of the product.

Plot descriptions should not be treated as free-form text fields. Instead, the product should use LLM-based classification to extract **structured, consistent signals** from IMDB plot descriptions.

### Plot source: TMDB overview
TMDB overviews are the free and comprehensive alternative to IMDB full plot descriptions. They are typically 2–5 sentences covering the film's premise and core conflict — sufficient for LLM-based theme extraction. They are available for nearly all films in the dataset via the Kaggle TMDB bulk download, with no API rate limits.

IMDB full synopses are more detailed but are not available in the free bulk datasets. They would require OMDb API calls at 1,000/day free tier, which is already being used for critic scores. TMDB overview is the practical free choice and covers the use case adequately.

### Theme extraction
The LLM should tag each film with one or more themes from a defined taxonomy. Example themes:

- class conflict / critique of elites
- revenge
- grief and loss
- family conflict
- coming of age
- survival
- technology / AI
- social satire
- romance across difference
- justice / corruption
- war / trauma
- identity / belonging
- power and control
- redemption
- isolation

The taxonomy should be treated as a starting point, not a fixed list. Themes that emerge consistently from the data but are not in the initial taxonomy should be added iteratively.

Each film receives:
- one or more theme tags
- a confidence score per tag
- source flag (which field was used: plot description, synopsis, or fallback)

### Narrative pattern extraction (secondary)
In addition to themes, the LLM can identify broader narrative structures:
- underdog arc
- revenge arc
- survival arc
- mystery / twist-driven
- ensemble story
- true story / biographical
- fish-out-of-water
- hero's journey

Narrative patterns are lighter than theme tagging in V1 but should be part of the data model from the start.

---

## Theme density and recurrence

A major objective is understanding not just what themes exist, but **how concentrated they are at a given time**.

Metrics:
- number of films tagged with a given theme per year / per quarter
- theme share of all releases in a period
- theme growth rate across years
- theme density band: rare / moderately common / crowded

This enables questions like:
- Is a theme emerging or declining?
- Are multiple films tackling the same theme in the same quarter — a cluster or a wave?
- Does theme crowding correlate with stronger or weaker outcomes?
- Are some themes recurrent but only successful in specific genres or languages?

---

## Key research questions

### 1. Release landscape
- How has the volume of releases changed from 2020 to 2026?
- What is the split across release types (streaming-only / theatrical / concurrent / theatrical-first)?
- Has streaming-only's share of notable releases grown over time?

### 2. Language trends
- What is the mix of English vs non-English films across the dataset?
- Are non-English films growing in share?
- How do language patterns relate to box office, reviews, and awards?

### 3. Genre-performance relationship
- Which genres are most common by release type?
- Which genres are strongest commercially, critically, and for awards?
- Are certain genres predominantly streaming-only?

### 4. Talent signal
- Which actors and directors appear most often?
- Which are associated with stronger commercial outcomes? Critical? Awards?
- Are there actors who are commercially strong but weak on awards, or vice versa?

### 5. Theme intelligence
- Which themes are most recurrent across the dataset?
- Which are growing in frequency over time?
- Are some themes crowded but underperforming?
- Are some themes rare but highly successful?
- Does success depend on the combination of theme + genre + language, not just theme alone?

### 6. Theme clustering over time
- Are there periods with concentrated theme clusters?
- Do these clusters correspond to cultural or political moments?
- When multiple films share a theme in the same quarter, do they amplify or cannibalize each other?

### 7. Reviews, ratings, and awards
- Are stronger critic scores associated with higher box office?
- Is this relationship consistent across genres and languages, or genre-specific?
- Are awards mostly associated with specific themes, genres, or narrative patterns?

### 8. Release type and outcomes
- Do streaming-only films perform differently on critic scores and awards than theatrical films?
- Are certain genres or themes predominantly streaming-only?
- How does theatrical-to-streaming delay relate to commercial or critical outcomes?

---

## Product outputs

The product helps users do 4 things:

### 1. Understand the release landscape
A view of 2020–2026 films by release type, language, genre, theme, and year — showing how the market has evolved.

### 2. Explore theme intelligence
Which themes are most common, which are growing, which cluster in time, and how theme frequency relates to different success modes.

### 3. Compare success modes
What correlates with box office vs. critical reception vs. awards — and where these diverge.

### 4. Explore talent and structural patterns
Actors, directors, genres, and release types in relation to outcome distributions.

---

## Product roadmap

### MVP — Theme Intelligence
**The core LLM pipeline.**

Deliverables:
- ingest IMDB plot descriptions for 2020–2026 films meeting the inclusion threshold
- LLM-based theme classification: extract themes from plot descriptions with confidence scores
- build theme taxonomy (initial list + iterative expansion)
- theme frequency and density metrics per year and per quarter
- theme cluster detection: which themes concentrate in the same period
- basic output: ranked theme list, theme-over-time chart, theme density view

This MVP demonstrates the core analytical capability and the LLM classification pattern — a transferable approach applicable to any text-based classification problem (e.g. interview analysis, customer feedback, content tagging).

---

### Iteration 2 — Market Overview
- release volume by year and quarter
- breakdown by release type (streaming-only / theatrical / concurrent / theatrical-first)
- breakdown by language and genre
- how the market composition has shifted from 2020 to 2026

---

### Iteration 3 — Success Explorer
- filter films by language, genre, theme, release type, and year
- show commercial / critical / awards outcomes side by side
- identify where success modes diverge (e.g. high box office but low critic scores)
- surface patterns across the filtered set

---

### Iteration 4 — Talent Explorer
- most frequent actors and directors in the dataset
- outcome distributions when they appear (box office, critic score, awards)
- comparison across success modes
- release type breakdown per talent

---

### Iteration 5 — Cross-dimensional synthesis
- theme + genre combinations and their outcome profiles
- theme + language patterns
- theme + release type patterns
- structural observations about which combinations over- or under-perform relative to their frequency

---

## Known gaps and future enrichment

These are data points that are acknowledged as missing from the current build, with notes on why and how they could be added later.

### days_to_streaming (reframed as days_to_digital)
**Status:** being populated via TMDB release_dates API (type 4 = digital release).

**What TMDB provides:** the `/movie/{id}/release_dates` endpoint includes a "digital" release type (type 4) for US releases. This captures when a film became available to buy or rent digitally (iTunes, Amazon VOD, etc.) — not necessarily when it landed on a subscription streaming platform like Netflix.

**Honest label:** this field should be presented as "theatrical-to-digital window" rather than "theatrical-to-streaming window." The distinction is real: a film might hit digital rental on day 45, then appear on Netflix on day 120.

**Coverage:** partial — not all films have a digital release date in TMDB. Coverage is best for major theatrical releases.

**Exact streaming subscription dates** (when a film first appeared on Netflix/Disney+/etc.) are not available from any free source. JustWatch has this data but no public API. This remains a longer-term enrichment opportunity.

---

## AI / LLM role

AI should be used where it adds real value and the output is auditable.

Good uses:
- extract structured themes from IMDB plot descriptions
- cluster similar plot descriptions
- generate or refine theme labels for clusters
- identify narrative patterns
- summarize how a theme is represented across multiple films

The LLM layer supports **classification, clustering, and labeling** — not prediction or recommendation. Outputs should always be inspectable and the taxonomy should be transparent.

Avoid framing AI outputs as definitive. Theme tags are model-generated and carry uncertainty.

---

## Product principles

### 1. Descriptive and diagnostic, not predictive
The product identifies patterns in past data. It does not predict outcomes for future films.

### 2. Correlation is not causation
The system identifies associations. No causal claims should be made.

### 3. Keep success modes separate
Commercial, critical, and awards success are different things and should be shown separately before any aggregation.

### 4. Theme frequency matters alongside theme performance
A theme should not be analyzed only by average outcome. How crowded it is matters too.

### 5. Combinations matter more than single attributes
Theme + genre + language + release type combinations are more informative than any single variable.

### 6. Transparency about data quality
Source flags, confidence scores, and coverage gaps should be visible — not hidden. This increases credibility.

---

## Recommended data model

### Movie
- id (TMDB)
- title
- release date
- original language
- genres
- cast (top-billed)
- director
- runtime
- franchise / original status
- release type (streaming-only / theatrical / concurrent / theatrical-first)
- streaming platform
- days to streaming (theatrical-first only)
- studio / distributor

### Plot and content signals
- plot overview (TMDB, via Kaggle bulk download)
- themes (array, LLM-extracted)
- theme confidence scores
- narrative pattern (LLM-extracted)
- cluster id

### Outcomes
- worldwide box office
- IMDB user rating
- IMDB vote count
- Rotten Tomatoes critic score
- Metacritic score
- awards text (raw OMDb string)
- oscar nominations / wins
- BAFTA nominations / wins
- Golden Globe nominations / wins
- festival awards (Cannes / Berlin / Venice / Sundance / other — semi-structured)
- total nominations count
- total wins count

---

## Limitations

The project should explicitly acknowledge:

- **Narrow time range**: 2020–2026 is six years, sufficient for trend observation but not for long-cycle pattern detection
- **Box office gaps**: streaming-only films have no box office data; worldwide revenue figures are often incomplete
- **Budget excluded**: public budget data is too unreliable (production cost only, excludes P&A) to support meaningful ROI analysis
- **Festival awards coverage**: international festival data requires manual enrichment and may be incomplete
- **Theme extraction uncertainty**: LLM theme tags are model-generated and depend on plot description quality; films with poor or missing plot descriptions will have lower-confidence tags
- **Awards sparsity**: award events are few per year; the awards signal is illustrative, not statistically robust
- **Survivorship bias in theatrical data**: the theatrical subset already represents films that cleared distribution and marketing thresholds — the selection effect should be noted when comparing theatrical vs. streaming
- **days_to_streaming not populated**: TMDB watch providers only shows current availability, not historical streaming release dates. This field is in the schema but empty. See "Known gaps" section for the enrichment plan.

Acknowledging limitations explicitly increases the credibility of the analysis and the maturity of the product framing.

---

## Portfolio positioning

This project demonstrates:

- **Structured problem decomposition**: breaking a messy question ("what makes a film successful?") into separable, measurable lenses
- **Metric design**: defining success modes independently before considering aggregation
- **LLM applied to classification**: using AI for structured extraction from unstructured text — a pattern transferable to interview analysis, customer feedback, content tagging, and other domains
- **Data realism**: making deliberate tradeoffs about what to include and exclude based on data reliability
- **Decision-support framing**: distinguishing between descriptive, diagnostic, and predictive analysis — and staying honest about which this product does

---

## One-line positioning statement

**ScreenTrend is a decision-support prototype that analyzes 2020–2026 films to understand how release type, talent, language, genre, and AI-derived themes relate to commercial success, critical reception, and awards recognition.**

---

## Compact Claude prompt

Build **ScreenTrend**, a portfolio-quality decision-support prototype for film analytics. Analyze 2020–2026 films (TMDB vote count ≥ 500) and show how movie attributes, release type (streaming-only / theatrical / concurrent / theatrical-first), language, cast, genre, and AI-derived themes relate to 3 separate success modes: commercial success, critical success, and awards success. Use the Kaggle TMDB bulk dataset as the primary source (free download, ~1M titles), IMDB non-commercial datasets for cast/crew and ratings, TMDB API for streaming provider data, and OMDb free tier for RT/Metacritic critic scores. TMDB overviews are used as the plot source for theme extraction. All data sources are free — total data cost is $0. The MVP is theme intelligence: use an LLM to extract structured themes from IMDB plot descriptions, build a theme taxonomy, measure theme recurrence and density over time, and detect theme clusters. This LLM classification pipeline is a core portfolio signal — it demonstrates the same pattern used in interview analysis, customer feedback tagging, and other text classification domains. The product is descriptive and diagnostic, not predictive.
