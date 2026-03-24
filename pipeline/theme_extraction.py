"""
Step 3: LLM-based theme extraction from TMDB overviews.

For each film, sends the overview to OpenAI and extracts:
  - themes (from a defined taxonomy, multi-label)
  - narrative_pattern (single label)
  - confidence per theme (0.0 - 1.0)

Results are written back to Supabase and to data/processed/themes.csv.

Cost estimate: ~$0.40 for 4,000 films using gpt-4o-mini.
"""

import os
import json
import time
import pandas as pd
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

from pipeline.db import get_client, fetch_movies

load_dotenv()

client_oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROCESSED = Path(__file__).parent.parent / "data" / "processed"

MODEL = "gpt-4o-mini"

THEMES = [
    "class conflict / critique of elites",
    "revenge",
    "grief and loss",
    "family conflict",
    "coming of age",
    "survival",
    "technology / AI",
    "social satire",
    "romance across difference",
    "justice / corruption",
    "war / trauma",
    "identity / belonging",
    "power and control",
    "redemption",
    "isolation",
]

NARRATIVE_PATTERNS = [
    "underdog arc",
    "revenge arc",
    "survival arc",
    "mystery / twist-driven",
    "ensemble story",
    "true story / biographical",
    "fish-out-of-water",
    "hero's journey",
    "none of the above",
]

SYSTEM_PROMPT = f"""You are a film analyst extracting structured thematic signals from movie plot summaries.

Given a movie title and its plot overview, return a JSON object with:
1. "themes": a list of 1–3 themes from the allowed list that best describe the film's content. Only include themes that are clearly present — do not force-fit.
2. "narrative_pattern": the single best-matching narrative structure from the allowed list.
3. "confidence": a dict mapping each selected theme to a confidence score between 0.0 and 1.0.

Allowed themes:
{json.dumps(THEMES, indent=2)}

Allowed narrative patterns:
{json.dumps(NARRATIVE_PATTERNS, indent=2)}

Return only valid JSON. No explanation, no markdown.

Example output:
{{
  "themes": ["revenge", "justice / corruption"],
  "narrative_pattern": "revenge arc",
  "confidence": {{"revenge": 0.95, "justice / corruption": 0.75}}
}}"""


def extract_themes_for_film(title: str, overview: str) -> dict:
    user_message = f"Title: {title}\n\nOverview: {overview}"
    try:
        response = client_oai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        result = json.loads(response.choices[0].message.content)

        # Validate: only keep themes that are in the allowed list
        result["themes"] = [t for t in result.get("themes", []) if t in THEMES]
        if result.get("narrative_pattern") not in NARRATIVE_PATTERNS:
            result["narrative_pattern"] = "none of the above"

        return result
    except Exception as e:
        print(f"  Error for '{title}': {e}")
        return {"themes": [], "narrative_pattern": "none of the above", "confidence": {}}


def run(batch_size: int = 50, delay: float = 0.1):
    """
    Extract themes for all films that don't yet have theme data.
    Writes results to Supabase and to data/processed/themes.csv.
    """
    db = get_client()

    # Fetch films without themes — paginate past Supabase's 1,000 row default
    films = []
    offset = 0
    while True:
        response = (
            db.table("movies")
            .select("id, title, overview")
            .is_("themes", "null")
            .range(offset, offset + 999)
            .execute()
        )
        batch = response.data
        films.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    if not films:
        print("All films already have theme data.")
        return

    print(f"Extracting themes for {len(films):,} films using {MODEL}...")

    results = []
    for film in tqdm(films, unit="film"):
        if not film.get("overview"):
            continue

        extracted = extract_themes_for_film(film["title"], film["overview"])
        record = {
            "id": film["id"],
            "themes": extracted.get("themes", []),
            "narrative_pattern": extracted.get("narrative_pattern"),
            "theme_confidence": extracted.get("confidence", {}),
        }
        results.append(record)

        # Write back to Supabase in batches
        if len(results) % batch_size == 0:
            _upsert_themes(db, results[-batch_size:])

        time.sleep(delay)  # gentle rate limiting

    # Final batch
    remainder = len(results) % batch_size
    if remainder:
        _upsert_themes(db, results[-remainder:])

    # Save locally as well
    df = pd.DataFrame(results)
    out = PROCESSED / "themes.csv"
    df.to_csv(out, index=False)
    print(f"\nTheme extraction complete. Results saved to {out}")
    return df


def _upsert_themes(db, records: list):
    for record in records:
        rid = record["id"]
        fields = {k: v for k, v in record.items() if k != "id"}
        db.table("movies").update(fields).eq("id", rid).execute()


if __name__ == "__main__":
    run()
