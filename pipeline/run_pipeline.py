"""
Master pipeline runner.

Usage:
  python -m pipeline.run_pipeline --step ingest
  python -m pipeline.run_pipeline --step load
  python -m pipeline.run_pipeline --step themes
  python -m pipeline.run_pipeline --all
"""

import argparse
from pathlib import Path


def step_ingest():
    from pipeline.ingest import run
    df = run()
    return df


def step_load():
    from pipeline.ingest import PROCESSED
    from pipeline.db import load_movies
    import pandas as pd

    path = PROCESSED / "movies_filtered.csv"
    if not path.exists():
        raise FileNotFoundError("Run --step ingest first.")
    df = pd.read_csv(path, low_memory=False)
    load_movies(df)


def step_themes():
    from pipeline.theme_extraction import run
    run()


def main():
    parser = argparse.ArgumentParser(description="ScreenTrend data pipeline")
    parser.add_argument("--step", choices=["ingest", "load", "themes"])
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    args = parser.parse_args()

    if args.all or args.step == "ingest":
        print("\n=== Step 1: Ingest + filter data ===")
        step_ingest()

    if args.all or args.step == "load":
        print("\n=== Step 2: Load into Supabase ===")
        step_load()

    if args.all or args.step == "themes":
        print("\n=== Step 3: LLM theme extraction ===")
        step_themes()

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
