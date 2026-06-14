#!/usr/bin/env bash
set -euo pipefail

: "${SUPABASE_DATABASE_URL:?Set SUPABASE_DATABASE_URL to your Supabase Postgres connection string.}"
: "${DATABASE_URL:?Set DATABASE_URL to your Neon Postgres connection string.}"

if [[ "$SUPABASE_DATABASE_URL" == *":6543/"* ]]; then
  echo "ERROR: SUPABASE_DATABASE_URL is using port 6543, the transaction pooler."
  echo "Use Supabase's session pooler connection string on port 5432 for pg_dump."
  exit 1
fi

dump_file="${1:-data/processed/supabase_movies_dump.sql}"
mkdir -p "$(dirname "$dump_file")"

echo "Dumping public.movies from Supabase..."
pg_dump "$SUPABASE_DATABASE_URL" \
  --table=public.movies \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --file="$dump_file"

echo "Restoring public.movies into Neon..."
psql "$DATABASE_URL" --file="$dump_file"

echo "Migration complete. Dump saved at $dump_file"
