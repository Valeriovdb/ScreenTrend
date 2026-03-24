"""
Fetch 2024-2026 films directly from TMDB API to supplement the Kaggle snapshot,
which has stale vote counts for recent films.

Produces: data/raw/tmdb_recent.csv
"""

import os
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW = Path(__file__).parent.parent / "data" / "raw"
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
BASE_URL = "https://api.themoviedb.org/3"

MIN_VOTES = 100
YEARS = [2024, 2025, 2026]


def get(endpoint: str, params: dict = None) -> dict:
    url = f"{BASE_URL}{endpoint}"
    p = {"api_key": TMDB_API_KEY, **(params or {})}
    r = requests.get(url, params=p, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_year(year: int) -> list[dict]:
    """Fetch all movies for a given year with vote_count >= MIN_VOTES."""
    print(f"  Fetching {year}...")
    results = []
    page = 1
    while True:
        data = get("/discover/movie", {
            "primary_release_year": year,
            "vote_count.gte": MIN_VOTES,
            "sort_by": "vote_count.desc",
            "page": page,
        })
        results.extend(data["results"])
        if page >= data["total_pages"] or page >= 50:  # TMDB caps at 500 pages
            break
        page += 1
        time.sleep(0.05)

    print(f"    {len(results)} films found")
    return results


def fetch_details(tmdb_id: int) -> dict:
    """Fetch full movie details including imdb_id, runtime, revenue."""
    data = get(f"/movie/{tmdb_id}", {"append_to_response": "external_ids"})
    return {
        "id": data.get("id"),
        "imdb_id": data.get("imdb_id") or data.get("external_ids", {}).get("imdb_id"),
        "title": data.get("title"),
        "original_title": data.get("original_title"),
        "release_date": data.get("release_date"),
        "original_language": data.get("original_language"),
        "genres": ", ".join(g["name"] for g in data.get("genres", [])),
        "runtime": data.get("runtime"),
        "overview": data.get("overview"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "popularity": data.get("popularity"),
        "revenue": data.get("revenue"),
        "production_companies": ", ".join(c["name"] for c in data.get("production_companies", [])),
    }


def run():
    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY not set in .env")

    all_films = []
    for year in YEARS:
        year_results = fetch_year(year)
        # Fetch full details for each (to get imdb_id, runtime, etc.)
        for i, film in enumerate(year_results):
            details = fetch_details(film["id"])
            details["release_year"] = year
            all_films.append(details)
            if (i + 1) % 50 == 0:
                print(f"    Detailed: {i+1}/{len(year_results)}")
            time.sleep(0.05)

    df = pd.DataFrame(all_films)
    out = RAW / "tmdb_recent.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df):,} recent films -> {out}")
    return df


if __name__ == "__main__":
    run()
