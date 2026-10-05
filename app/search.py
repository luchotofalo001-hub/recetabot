from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from app.extract import fold

PANTRY = {"sal", "pimienta", "agua", "aceite", "aceite de oliva"}

SYNONYMS = {
    "papa": "papa",
    "papas": "papa",
    "patata": "papa",
    "batata": "batata",
    "boniato": "batata",
    "zapallo": "zapallo",
    "calabaza": "zapallo",
    "morron": "morrón",
    "morrón": "morrón",
    "pimiento": "morrón",
    "frutilla": "frutilla",
    "fresa": "frutilla",
    "manteca": "manteca",
    "mantequilla": "manteca",
    "choclo": "choclo",
    "maiz": "choclo",
    "maíz": "choclo",
    "poroto": "poroto",
    "frijol": "poroto",
    "judia": "poroto",
    "arveja": "arveja",
    "guisante": "arveja",
    "palta": "palta",
    "aguacate": "palta",
    "pollo": "pollo",
    "pechuga": "pollo",
    "carne": "carne",
    "cerdo": "cerdo",
    "pescado": "pescado",
    "huevo": "huevo",
    "huevos": "huevo",
    "queso": "queso",
    "muzarella": "mozzarella",
    "mozzarella": "mozzarella",
    "cebolla": "cebolla",
    "ajo": "ajo",
    "tomate": "tomate",
    "arroz": "arroz",
    "fideos": "fideos",
    "pasta": "fideos",
    "leche": "leche",
    "harina": "harina",
    "limon": "limón",
    "limón": "limón",
}


def canon_ingredient(token: str) -> str:
    t = fold(token).strip()
    return SYNONYMS.get(t, token.strip().lower())


def _coverage(recipe_ings: list[str], have: set[str]) -> float:
    needed = [i for i in recipe_ings if fold(i) not in PANTRY and i not in PANTRY]
    if not needed:
        return 0.4
    hit = 0
    for ing in needed:
        key = fold(ing)
        if key in have or ing in have or any(key in h or h in key for h in have):
            hit += 1
    return hit / len(needed)


def _cooked_recent(feedback: list[dict[str, Any]], hours: int = 48) -> set[str]:
    limit = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = set()
    for row in feedback:
        if row.get("kind") != "cooked":
            continue
        raw = row.get("created_at") or ""
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= limit:
            out.add(row["recipe_id"])
    return out


def _likes_fails(feedback: list[dict[str, Any]]) -> tuple[dict[str, int], set[str]]:
    likes: dict[str, int] = {}
    fails = set()
    for row in feedback:
        rid = row.get("recipe_id")
        if not rid:
            continue
        if row.get("kind") == "liked":
            likes[rid] = likes.get(rid, 0) + 1
        elif row.get("kind") == "failed":
            fails.add(rid)
    return likes, fails


def search_slot(
    recipes: list[dict[str, Any]],
    feedback: list[dict[str, Any]],
    *,
    diet: str,
    have: list[str],
    exclude: list[str],
    max_minutes: int | None,
    meal: str | None,
    query: str | None,
    avoid_ids: set[str],
    limit: int = 3,
    allow_recent: bool = False,
) -> list[dict[str, Any]]:
    have_set = {canon_ingredient(x) for x in have}
    have_set |= {fold(x) for x in have_set}
    exclude_set = {fold(canon_ingredient(x)) for x in exclude}
    recent = set() if allow_recent else _cooked_recent(feedback)
    likes, fails = _likes_fails(feedback)
    q = fold(query or "")
    scored: list[tuple[float, dict[str, Any]]] = []
    for rec in recipes:
        rid = rec["id"]
        if rid in avoid_ids:
            continue
        if rid in fails and not q:
            continue
        if rid in recent and not q:
            continue
        if diet == "vegetarian" and not rec.get("vegetarian"):
            continue
        if diet == "vegan" and not rec.get("vegan"):
            continue
        if diet == "meat" and rec.get("vegetarian"):
            continue
        if max_minutes and (rec.get("minutes") or 999) > max_minutes:
            continue
        if meal == "postre" and "postre" not in (rec.get("tags") or []):
            continue
        if meal in {"cena", "almuerzo"} and "postre" in (rec.get("tags") or []) and diet != "any":
            # cena salada por defecto si no pidieron postre
            if meal and "postre" not in (q or ""):
                continue
        ings = rec.get("ingredients") or []
        if exclude_set and any(fold(i) in exclude_set for i in ings):
            continue
        title_f = fold(rec.get("title") or "")
        if q and q not in title_f and not any(q in fold(i) for i in ings):
            continue
        score = 1.0
        if have_set:
            cov = _coverage(ings, have_set)
            if cov < 0.45 and not q:
                continue
            score += cov * 5
        score += likes.get(rid, 0) * 2.5
        if rec.get("custom"):
            score += 0.4
        if rec.get("incomplete"):
            score -= 1.5
        if rec.get("vegetarian") and diet == "any":
            score -= 0.15
        minutes = rec.get("minutes") or 60
        if max_minutes:
            score += max(0, (max_minutes - minutes) / 40)
        scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in scored[:limit]]


def format_option(index: int, rec: dict[str, Any]) -> str:
    ings = ", ".join((rec.get("ingredients") or [])[:8]) or "sin ingredientes detectados"
    mins = rec.get("minutes") or "?"
    flag = "vegetariana" if rec.get("vegetarian") else "con proteína animal"
    own = " · tuya" if rec.get("custom") else ""
    return f"{index}. {rec.get('title')} ({mins} min, {flag}{own})\n   {ings}"


def format_detail(rec: dict[str, Any]) -> str:
    amounts = rec.get("amounts") or []
    if amounts:
        ings = "\n".join(f"• {i}" for i in amounts)
        label = "Ingredientes"
    else:
        ings = "\n".join(f"• {i}" for i in (rec.get("ingredients") or [])) or "• (sin cantidades en el origen)"
        label = "Ingredientes detectados, sin cantidades"
    proc = (rec.get("procedure") or "").strip()
    proc = re.sub(r"\n{3,}", "\n\n", proc)
    if len(proc) > 2800:
        proc = proc[:2800] + "…"
    url = rec.get("url") or ""
    extra = f"\n\n{url}" if url else ""
    return (
        f"*{rec.get('title')}*\n"
        f"Tiempo estimado: {rec.get('minutes')} min · "
        f"{'vegetariana' if rec.get('vegetarian') else 'no vegetariana'}\n\n"
        f"{label}:\n{ings}\n\n"
        f"{proc}{extra}"
    )
