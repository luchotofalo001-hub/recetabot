"""Carga las recetas scrapeadas en Supabase. Uso:
PYTHONPATH=. python scripts/seed_supabase.py /ruta/cocineros_recetas.db
"""
from __future__ import annotations

import os
import sqlite3
import sys

from supabase import create_client

from app.extract import estimate_minutes, extract_ingredients, is_vegan, is_vegetarian, meal_tags

STUB = "organizá los ingredientes antes de empezar"


def category(url: str) -> str:
    parts = (url or "").rstrip("/").split("/")
    if "recetas" in parts:
        i = parts.index("recetas")
        if i + 1 < len(parts):
            return parts[i + 1]
    return ""


def main() -> None:
    db_path = sys.argv[1]
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    conn = sqlite3.connect(db_path)
    rows = conn.execute("select url, titulo, procedimiento from recetas").fetchall()
    batch = []
    for url, title, procedure in rows:
        title = title or "Sin título"
        procedure = procedure or ""
        cat = category(url)
        if cat in {"pollo", "carne", "bebidas", "apto-celiaco", "arroces-y-pastas"} and len(procedure) < 40:
            continue
        ings = extract_ingredients(title, procedure)
        incomplete = STUB in procedure.lower() and len(procedure) < 420
        batch.append(
            {
                "external_id": url,
                "title": title,
                "category": cat,
                "url": url,
                "procedure": procedure,
                "ingredients": ings,
                "minutes": estimate_minutes(procedure, title),
                "vegetarian": is_vegetarian(ings, title, cat),
                "vegan": is_vegan(ings, title, cat),
                "tags": meal_tags(title, cat),
                "custom": False,
                "incomplete": incomplete,
            }
        )
        if len(batch) == 200:
            sb.table("recipes").upsert(batch, on_conflict="external_id").execute()
            batch = []
            print(".", end="", flush=True)
    if batch:
        sb.table("recipes").upsert(batch, on_conflict="external_id").execute()
    print("\nlisto", len(rows))


if __name__ == "__main__":
    main()
