"""
Fetch TMDB watch providers + digital release dates for all films.

Release type logic:
  - revenue > 1M  AND  streaming available  → theatrical_first
  - revenue > 1M  AND  no streaming found   → theatrical
  - revenue = 0   AND  streaming available  → streaming_only
  - revenue = 0   AND  no streaming         → unknown

Also fetches TMDB release_dates (type 4 = digital/VOD) to populate
days_to_digital — the gap between theatrical and digital release.
Note: digital release = available to buy/rent, not necessarily streaming subscription.
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

TMDB_API_KEY = os.environ["TMDB_API_KEY"]
BASE_URL = "https://api.themoviedb.org/3"
REGION = "US"

STREAMING_PLATFORMS = {
    8:   "Netflix",
    9:   "Amazon Prime",
    337: "Disney+",
    350: "Apple TV+",
    384: "HBO Max",
    531: "Paramount+",
    386: "Peacock",
    387: "Peacock",
    15:  "Hulu",
    283: "Crunchyroll",
}


def get_providers(tmdb_id: int) -> dict:
    r = requests.get(
        f"{BASE_URL}/movie/{tmdb_id}/watch/providers",
        params={"api_key": TMDB_API_KEY}, timeout=10
    )
    if r.status_code != 200:
        return {}
    return r.json().get("results", {}).get(REGION, {})


def get_digital_release_date(tmdb_id: int):
    """Returns the digital release date (type 4) for US, or None."""
    r = requests.get(
        f"{BASE_URL}/movie/{tmdb_id}/release_dates",
        params={"api_key": TMDB_API_KEY}, timeout=10
    )
    if r.status_code != 200:
        return None
    results = r.json().get("results", [])
    for country in results:
        if country.get("iso_3166_1") != "US":
            continue
        for rd in country.get("release_dates", []):
            if rd.get("type") == 4:  # digital
                date_str = rd.get("release_date", "")[:10]
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return None
    return None


def classify(revenue, providers: dict):
    """Returns (release_type, streaming_platform)."""
    flatrate = providers.get("flatrate", [])
    platform = None
    for item in flatrate:
        pid = item.get("provider_id")
        if pid in STREAMING_PLATFORMS:
            platform = STREAMING_PLATFORMS[pid]
            break

    has_revenue = isinstance(revenue, (int, float)) and revenue > 1_000_000
    on_streaming = platform is not None

    if has_revenue and on_streaming:
        return "theatrical_first", platform
    elif has_revenue and not on_streaming:
        return "theatrical", None
    elif not has_revenue and on_streaming:
        return "streaming_only", platform
    else:
        return "unknown", None


def run():
    from pipeline.db import get_client

    client = get_client()

    # Paginate past Supabase's 1,000 row default
    films = []
    page_size = 1000
    offset = 0
    while True:
        response = (
            client.table("movies")
            .select("id, revenue, release_date")
            .is_("release_type", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data
        films.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    print(f"Fetching watch providers + digital dates for {len(films):,} films...")

    updates = []
    for film in tqdm(films, unit="film"):
        providers = get_providers(film["id"])
        release_type, platform = classify(film.get("revenue"), providers)

        # Digital release date (type 4) — proxy for theatrical-to-digital window
        digital_date = get_digital_release_date(film["id"])
        days_to_digital = None
        if digital_date and film.get("release_date"):
            try:
                theatrical_date = datetime.strptime(film["release_date"][:10], "%Y-%m-%d").date()
                diff = (digital_date - theatrical_date).days
                days_to_digital = diff if diff >= 0 else None
            except ValueError:
                pass

        updates.append({
            "id": film["id"],
            "release_type": release_type,
            "streaming_platform": platform,
            "days_to_streaming": days_to_digital,  # labelled as proxy in schema
        })
        time.sleep(0.1)  # two API calls per film — slightly more conservative

    # Write back — use update().eq() per row since upsert requires all NOT NULL cols
    print("\nWriting to Supabase...")
    for i, u in enumerate(updates):
        client.table("movies").update({
            "release_type":       u["release_type"],
            "streaming_platform": u["streaming_platform"],
            "days_to_streaming":  u["days_to_streaming"],
        }).eq("id", u["id"]).execute()
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(updates)}", end="\r")

    print(f"\nDone.")
    rt = pd.Series([u["release_type"] for u in updates]).value_counts()
    print("Release type breakdown:\n", rt.to_string())
    filled = sum(1 for u in updates if u["days_to_streaming"] is not None)
    print(f"days_to_digital populated: {filled}/{len(updates)} films ({filled/len(updates)*100:.0f}%)")


if __name__ == "__main__":
    run()
