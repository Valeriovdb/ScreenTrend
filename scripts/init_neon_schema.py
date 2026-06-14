"""
Create the ScreenTrend schema in Neon.

Usage:
  python3 scripts/init_neon_schema.py
"""

from pipeline.db import init_schema


if __name__ == "__main__":
    init_schema()
    print("Neon schema is ready.")
