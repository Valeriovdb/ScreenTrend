"""
Fetch streaming availability dates from Movie of the Night API (via RapidAPI).

For each film, retrieves when it was first added to major streaming platforms
(Netflix, Amazon Prime, Disney+, Apple TV+, HBO Max, etc.) in the US.

This is more precise than TMDB's digital release date (type 4), which captures
buy/rent availability rather than subscription streaming.

Rate limit: 100 requests/day on free tier.
The script tracks progress in data/processed/streaming_dates_progress.csv
so it can be run daily and pick up where it left off.

Usage:
  python3 -m pipeline.streaming_dates          # fetch next 100 films
  python3 -m pipeline.streaming_dates --status  # show progress summary
"""

import os
import time
import argparse
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
PROCESSED = Path(__file__).parent.parent / "data" / "processed"
PROGRESS_FILE = PROCESSED / "streaming_dates_progress.csv"

RAPIDAPI_HOST = "streaming-availability.p.rapidapi.com"
BASE_URL = "https://streaming-availability.p.rapidapi.com"

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
}

DAILY_LIMIT = 100  # free tier cap


def get_streaming_dates(imdb_id: str) -> dict:
    """
    Fetch streaming availability for a film by IMDB ID.
    Returns dict of {platform: first_seen_date} for US.
    """
    url = f"{BASE_URL}/shows/{imdb_id}"
    params = {"series_granularity": "show", "output_language": "en"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)

    if r.status_code == 404:
        return {}
    if r.status_code == 429:
        raise RuntimeError("Rate limit hit — daily quota exhausted.")
    r.raise_for_status()

    data = r.json()
    streaming_options = data.get("streamingOptions", {}).get("us", [])

    result = {}
    for option in streaming_options:
        if option.get("type") != "subscription":
            continue
        service = option.get("service", {}).get("name")
        added_on = option.get("availableSince")  # Unix timestamp
        if service and added_on:
            date = datetime.utcfromtimestamp(added_on).strftime("%Y-%m-%d")
            # Keep earliest date per platform
            if service not in result or date < result[service]:
                result[service] = date

    return result


def load_progress() -> pd.DataFrame:
    if PROGRESS_FILE.exists():
        return pd.read_csv(PROGRESS_FILE)
    return pd.DataFrame(columns=["id", "imdb_id", "status", "streaming_dates", "fetched_at"])


def save_progress(df: pd.DataFrame):
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROGRESS_FILE, index=False)


def run(limit: int = DAILY_LIMIT):
    from pipeline.db import get_client

    client = get_client()
    progress = load_progress()
    done_ids = set(progress["id"].tolist()) if not progress.empty else set()

    # Fetch all films with imdb_id not yet processed
    films = []
    page_size = 1000
    offset = 0
    while True:
        r = client.table("movies").select("id, imdb_id, release_date").range(
            offset, offset + page_size - 1
        ).execute()
        batch = r.data
        films.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    pending = [f for f in films if f["id"] not in done_ids and f.get("imdb_id")]
    print(f"Progress: {len(done_ids)}/{len(films)} films fetched. {len(pending)} remaining.")
    print(f"Fetching next {min(limit, len(pending))} films...\n")

    new_rows = []
    updates = []

    for film in pending[:limit]:
        try:
            dates = get_streaming_dates(film["imdb_id"])
            status = "found" if dates else "not_found"

            # Calculate days_to_streaming from earliest platform date
            earliest = min(dates.values()) if dates else None
            days_to_streaming = None
            if earliest and film.get("release_date"):
                try:
                    release = datetime.strptime(film["release_date"][:10], "%Y-%m-%d")
                    digital = datetime.strptime(earliest, "%Y-%m-%d")
                    diff = (digital - release).days
                    days_to_streaming = diff if diff >= 0 else None
                except ValueError:
                    pass

            # Primary platform = platform with earliest date
            primary_platform = None
            if dates:
                primary_platform = min(dates, key=dates.get)

            new_rows.append({
                "id": film["id"],
                "imdb_id": film["imdb_id"],
                "status": status,
                "streaming_dates": str(dates) if dates else None,
                "fetched_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })
            updates.append({
                "id": film["id"],
                "days_to_streaming": days_to_streaming,
                "streaming_platform": primary_platform or None,
            })

            symbol = "✓" if dates else "·"
            print(f"  {symbol} {film['imdb_id']} — {primary_platform or 'not on streaming'}")
            time.sleep(0.3)

        except RuntimeError as e:
            print(f"\n{e}")
            break
        except Exception as e:
            print(f"  ✗ {film['imdb_id']} — error: {e}")
            new_rows.append({
                "id": film["id"],
                "imdb_id": film["imdb_id"],
                "status": "error",
                "streaming_dates": None,
                "fetched_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })

    # Save progress
    progress = pd.concat([progress, pd.DataFrame(new_rows)], ignore_index=True)
    save_progress(progress)
    print(f"\nProgress saved: {len(progress)}/{len(films)} films done.")

    # Write to Supabase
    if updates:
        print("Writing to Supabase...")
        batch_size = 100
        for i in range(0, len(updates), batch_size):
            client.table("movies").upsert(
                updates[i:i + batch_size], on_conflict="id"
            ).execute()
        print(f"  {len(updates)} films updated.")


def status():
    progress = load_progress()
    if progress.empty:
        print("No progress yet.")
        return
    print(f"Total fetched: {len(progress)}")
    print(progress["status"].value_counts().to_string())
    found = progress[progress["status"] == "found"]
    print(f"\nFilms with streaming dates: {len(found)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--limit", type=int, default=DAILY_LIMIT)
    args = parser.parse_args()

    if args.status:
        status()
    else:
        run(limit=args.limit)
