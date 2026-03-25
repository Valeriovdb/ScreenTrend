"""
Database helpers: Supabase schema creation and data loading.
"""

import os
import math
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# SQL to create the movies table — run this once in the Supabase SQL editor
CREATE_TABLE_SQL = """
create table if not exists movies (
    id            bigint primary key,           -- TMDB id
    imdb_id       text,
    title         text not null,
    original_title text,
    release_date  date,
    release_year  int,
    original_language text,
    genres        text,
    runtime       float,
    overview      text,
    vote_average  float,
    vote_count    int,
    popularity    float,
    revenue       bigint,
    top_cast      text,
    director      text,
    imdb_rating   float,
    imdb_votes    int,
    -- theme extraction (populated later)
    themes        text[],
    narrative_pattern text,
    theme_confidence jsonb,
    -- awards (populated later via manual enrichment)
    oscar_nominations int default 0,
    oscar_wins        int default 0,
    bafta_nominations int default 0,
    bafta_wins        int default 0,
    golden_globe_nominations int default 0,
    golden_globe_wins        int default 0,
    festival_awards   jsonb,                    -- {cannes: "Palme d'Or", berlin: null, ...}
    total_nominations int default 0,
    total_wins        int default 0,
    -- critic scores (populated later via OMDb)
    rt_score      int,
    metacritic    int,
    -- release type (populated later via TMDB watch providers)
    release_type  text,                         -- streaming_only / theatrical / concurrent / theatrical_first
    streaming_platform text,
    days_to_streaming int,
    created_at    timestamptz default now()
);

-- Indexes for common query patterns
create index if not exists idx_movies_release_year on movies(release_year);
create index if not exists idx_movies_language on movies(original_language);
create index if not exists idx_movies_release_type on movies(release_type);
create index if not exists idx_movies_themes on movies using gin(themes);
"""


def load_movies(df: pd.DataFrame, batch_size: int = 100):
    """Upsert movies dataframe into Supabase."""
    client = get_client()

    # Clean: replace NaN with None for JSON compatibility
    df = df.where(pd.notna(df), None)

    # Convert int columns that may be stored as floats (e.g. 2024.0 -> 2024)
    int_cols = ["vote_count", "imdb_votes", "revenue", "release_year", "runtime"]
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)

    records = [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]
    total = len(records)

    print(f"Upserting {total:,} films to Supabase...")
    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        client.table("movies").upsert(batch).execute()
        print(f"  {min(i + batch_size, total)}/{total}", end="\r")

    print(f"\nDone — {total:,} films loaded.")


def paginate_all(client, table: str, select: str, filters: list = None, page_size: int = 1000) -> list:
    """Fetch all rows from a Supabase table, bypassing the default 1,000 row limit."""
    rows = []
    offset = 0
    while True:
        q = client.table(table).select(select)
        if filters:
            for method, col, val in filters:
                q = getattr(q, method)(col, val)
        batch = q.range(offset, offset + page_size - 1).execute().data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def fetch_movies(filters: dict = None) -> pd.DataFrame:
    """Fetch movies from Supabase with optional filters."""
    client = get_client()
    query = client.table("movies").select("*")

    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)

    response = query.execute()
    return pd.DataFrame(response.data)
