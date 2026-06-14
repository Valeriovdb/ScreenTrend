"""
Database helpers for ScreenTrend's Postgres database.

The project uses Neon in production, but this module only depends on a standard
Postgres DATABASE_URL so it also works with local Postgres if needed.
"""

import math
import os
from typing import Any, Optional, Union

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
MOVIES_TABLE = "public.movies"

MOVIE_COLUMNS = {
    "id",
    "imdb_id",
    "title",
    "original_title",
    "release_date",
    "release_year",
    "original_language",
    "genres",
    "runtime",
    "overview",
    "vote_average",
    "vote_count",
    "popularity",
    "revenue",
    "top_cast",
    "director",
    "imdb_rating",
    "imdb_votes",
    "production_companies",
    "production_countries",
    "status",
    "tagline",
    "themes",
    "narrative_pattern",
    "theme_confidence",
    "oscar_nominations",
    "oscar_wins",
    "bafta_nominations",
    "bafta_wins",
    "golden_globe_nominations",
    "golden_globe_wins",
    "festival_awards",
    "total_nominations",
    "total_wins",
    "rt_score",
    "metacritic",
    "release_type",
    "streaming_platform",
    "days_to_streaming",
    "created_at",
}

JSONB_COLUMNS = {"theme_confidence", "festival_awards"}


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
    production_companies text,
    production_countries text,
    status        text,
    tagline       text,
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


def get_connection() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Add your Neon pooled connection string to .env."
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None)


def init_schema() -> None:
    """Create the movies table and indexes if they do not exist."""
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)


def _clean_value(column: str, value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value) if not isinstance(value, (list, dict)) else False:
        return None
    if column in JSONB_COLUMNS and isinstance(value, dict):
        return Jsonb(value)
    return value


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        column: _clean_value(column, value)
        for column, value in record.items()
        if column in MOVIE_COLUMNS
    }


def _column_list(columns: Union[list[str], tuple[str, ...], str]) -> str:
    if columns == "*":
        return "*"
    invalid = set(columns) - MOVIE_COLUMNS
    if invalid:
        raise ValueError(f"Unknown movie columns: {', '.join(sorted(invalid))}")
    return ", ".join(columns)


def _upsert_records(records: list[dict[str, Any]], batch_size: int = 100) -> None:
    if not records:
        return

    columns = sorted(set().union(*(record.keys() for record in records)))
    if "id" not in columns:
        raise ValueError("Upsert records must include an id.")

    placeholders = ", ".join(f"%({column})s" for column in columns)
    column_sql = ", ".join(columns)
    update_sql = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in {"id", "created_at"}
    )
    sql = f"""
        insert into {MOVIES_TABLE} ({column_sql})
        values ({placeholders})
        on conflict (id) do update set {update_sql}
    """

    rows = [{column: record.get(column) for column in columns} for record in records]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                cur.executemany(sql, rows[i : i + batch_size])


def update_movies(records: list[dict[str, Any]], batch_size: int = 100) -> None:
    """Update existing movie rows by id."""
    if not records:
        return

    columns = sorted(set().union(*(record.keys() for record in records)) - {"id"})
    if not columns:
        return

    invalid = set(columns) - MOVIE_COLUMNS
    if invalid:
        raise ValueError(f"Unknown movie columns: {', '.join(sorted(invalid))}")

    set_sql = ", ".join(f"{column} = %({column})s" for column in columns)
    sql = f"update {MOVIES_TABLE} set {set_sql} where id = %(id)s"
    rows = [
        _clean_record({column: record.get(column) for column in [*columns, "id"]})
        for record in records
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                cur.executemany(sql, rows[i : i + batch_size])


def update_movie(movie_id: int, fields: dict[str, Any]) -> None:
    update_movies([{"id": movie_id, **fields}], batch_size=1)


def load_movies(df: pd.DataFrame, batch_size: int = 100) -> None:
    """Upsert a movies dataframe into Postgres."""
    init_schema()
    df = df.where(pd.notna(df), None)

    int_cols = ["vote_count", "imdb_votes", "revenue", "release_year"]
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)

    records = [_clean_record(row) for row in df.to_dict(orient="records")]
    total = len(records)

    print(f"Upserting {total:,} films to Postgres...")
    _upsert_records(records, batch_size=batch_size)
    print(f"Done - {total:,} films loaded.")


def fetch_movies(
    filters: Optional[dict[str, Any]] = None,
    columns: Union[list[str], tuple[str, ...], str] = "*",
) -> pd.DataFrame:
    """Fetch movies with optional equality filters."""
    select_sql = _column_list(columns)
    params = {}
    where = []

    if filters:
        invalid = set(filters) - MOVIE_COLUMNS
        if invalid:
            raise ValueError(f"Unknown movie columns: {', '.join(sorted(invalid))}")
        for index, (column, value) in enumerate(filters.items()):
            key = f"filter_{index}"
            where.append(f"{column} = %({key})s")
            params[key] = value

    where_sql = f" where {' and '.join(where)}" if where else ""
    with get_connection() as conn:
        rows = conn.execute(f"select {select_sql} from {MOVIES_TABLE}{where_sql}", params).fetchall()
    return pd.DataFrame(rows)


def fetch_movie_rows(
    columns: Union[list[str], tuple[str, ...], str] = "*",
    where_sql: str = "",
    params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Fetch movie rows for pipeline jobs that need simple SQL predicates."""
    select_sql = _column_list(columns)
    predicate = f" where {where_sql}" if where_sql else ""
    with get_connection() as conn:
        return conn.execute(
            f"select {select_sql} from {MOVIES_TABLE}{predicate}",
            params or {},
        ).fetchall()
