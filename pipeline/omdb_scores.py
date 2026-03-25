"""
Fetch RT and Metacritic scores from OMDb API.

Free tier: 1,000 requests/day.
Tracks progress in data/processed/omdb_progress.csv so it can
be run daily via GitHub Actions and pick up where it left off.

Usage:
  python3 -m pipeline.omdb_scores           # fetch next 1,000 films
  python3 -m pipeline.omdb_scores --status  # show progress
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

OMDB_API_KEY = os.environ["OMDB_API_KEY"]
BASE_URL = "http://www.omdbapi.com"
PROCESSED = Path(__file__).parent.parent / "data" / "processed"
PROGRESS_FILE = PROCESSED / "omdb_progress.csv"
DAILY_LIMIT = 1000


def fetch_scores(imdb_id: str) -> dict:
    r = requests.get(
        BASE_URL,
        params={"apikey": OMDB_API_KEY, "i": imdb_id, "tomatoes": "true"},
        timeout=10,
    )
    if r.status_code != 200:
        return {}
    data = r.json()
    if data.get("Response") == "False":
        return {}

    rt_score = None
    metacritic = None

    # RT score from Ratings array
    for rating in data.get("Ratings", []):
        if rating.get("Source") == "Rotten Tomatoes":
            try:
                rt_score = int(rating["Value"].replace("%", ""))
            except (ValueError, KeyError):
                pass

    # Metacritic from dedicated field
    meta_raw = data.get("Metascore", "N/A")
    if meta_raw not in ("N/A", "", None):
        try:
            metacritic = int(meta_raw)
        except ValueError:
            pass

    return {"rt_score": rt_score, "metacritic": metacritic}


def load_progress() -> pd.DataFrame:
    if PROGRESS_FILE.exists():
        return pd.read_csv(PROGRESS_FILE)
    return pd.DataFrame(columns=["id", "imdb_id", "status", "fetched_at"])


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
    offset = 0
    while True:
        r = client.table("movies").select("id, imdb_id").range(
            offset, offset + 999
        ).execute()
        films.extend(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000

    pending = [f for f in films if f["id"] not in done_ids and f.get("imdb_id")]
    print(f"Progress: {len(done_ids)}/{len(films)} fetched. {len(pending)} remaining.")
    to_fetch = pending[:limit]
    print(f"Fetching {len(to_fetch)} films...\n")

    new_rows = []
    updates = []

    for film in to_fetch:
        try:
            scores = fetch_scores(film["imdb_id"])
            status = "found" if (scores.get("rt_score") or scores.get("metacritic")) else "not_found"
            new_rows.append({
                "id": film["id"],
                "imdb_id": film["imdb_id"],
                "status": status,
                "fetched_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })
            if scores:
                updates.append({"id": film["id"], **scores})

            symbol = "✓" if status == "found" else "·"
            print(f"  {symbol} {film['imdb_id']}  RT={scores.get('rt_score')}  MC={scores.get('metacritic')}")
            time.sleep(0.15)

        except Exception as e:
            print(f"  ✗ {film['imdb_id']} — {e}")
            new_rows.append({
                "id": film["id"],
                "imdb_id": film["imdb_id"],
                "status": "error",
                "fetched_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })

    # Save progress
    progress = pd.concat([progress, pd.DataFrame(new_rows)], ignore_index=True)
    save_progress(progress)

    # Write scores to Supabase in batches
    if updates:
        print(f"\nWriting {len(updates)} score updates to Supabase...")
        batch_size = 100
        for i in range(0, len(updates), batch_size):
            client.table("movies").upsert(
                updates[i:i + batch_size], on_conflict="id"
            ).execute()
        print("Done.")

    found = sum(1 for r in new_rows if r["status"] == "found")
    print(f"\nSummary: {found}/{len(new_rows)} films had RT or Metacritic scores.")


def status():
    progress = load_progress()
    if progress.empty:
        print("No progress yet.")
        return
    print(f"Total fetched: {len(progress)}")
    print(progress["status"].value_counts().to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--limit", type=int, default=DAILY_LIMIT)
    args = parser.parse_args()
    if args.status:
        status()
    else:
        run(limit=args.limit)
