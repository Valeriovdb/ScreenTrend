"""
Step 1: Filter the TMDB dataset.

Source:  data/raw/TMDB_all_movies.csv  (alanvourch/tmdb-movies-daily-updates)
         Already includes: cast, director, IMDB rating/votes, overview, revenue.
         No IMDB dataset merge needed.

Produces: data/processed/movies_filtered.csv
  ~2,300 films, 2020–2026, vote_count >= 200, has overview.
"""

import pandas as pd
from pathlib import Path

RAW = Path(__file__).parent.parent / "data" / "raw"
PROCESSED = Path(__file__).parent.parent / "data" / "processed"

TMDB_FILE = "TMDB_all_movies.csv"
MIN_VOTES = 200
MIN_YEAR = 2020
MAX_YEAR = 2026


def run() -> pd.DataFrame:
    path = RAW / TMDB_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found.\n"
            "Download it with:\n"
            "  kaggle datasets download -d alanvourch/tmdb-movies-daily-updates -p data/raw --unzip"
        )

    print("Loading TMDB dataset...")
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    print(f"  Raw rows: {len(df):,}")

    # Year filter
    df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year
    df = df[(df["release_year"] >= MIN_YEAR) & (df["release_year"] <= MAX_YEAR)]

    # Vote threshold
    df = df[df["vote_count"] >= MIN_VOTES]

    # Must have overview
    df = df[df["overview"].notna() & (df["overview"].str.strip() != "")]

    # Exclude adult titles
    if "adult" in df.columns:
        df = df[df["adult"].astype(str).str.lower() != "true"]

    # Standardise columns — keep what the rest of the pipeline expects
    keep = [
        "id", "imdb_id", "title", "original_title",
        "release_date", "release_year",
        "original_language", "genres", "runtime", "overview",
        "vote_average", "vote_count", "popularity", "revenue",
        "cast", "director",
        "imdb_rating", "imdb_votes",
        "production_companies", "production_countries",
        "status", "tagline",
    ]
    df = df[[c for c in keep if c in df.columns]].reset_index(drop=True)

    # Rename cast -> top_cast for consistency with db schema
    df = df.rename(columns={"cast": "top_cast"})

    print(f"  Filtered: {len(df):,} films")
    print()
    print(df["release_year"].value_counts().sort_index().to_string())

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "movies_filtered.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved -> {out}")
    return df


if __name__ == "__main__":
    run()
