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


MEAT_WORDS = ("higado", "molleja", "milanesa", "chorizo", "morcilla", "panceta", "bacon", "tocino", "jamon", "bondiola", "asado", "vacio", "entrana", "pollo", "cerdo", "pescado", "atun", "salmon", "langostino", "gamba", "camaron", "cordero", "ternera", "vacuno", "carne", "lomo", "merluza", "pulpo", "calamar", "mejillon", "almeja", "salchicha", "longaniza", "costilla", "matambre", "bife", "churrasco", "pavo", "pato", "anchoa", "prosciutto")


def is_veg(rec: dict[str, Any]) -> bool:
    title = fold(rec.get("title") or "")
    blob = title + " " + " ".join(fold(i) for i in (rec.get("ingredients") or [])) + " " + " ".join(fold(i) for i in (rec.get("amounts") or []))
    return not any(w in blob for w in MEAT_WORDS)
SWEET = ("torta", "budin", "flan", "helado", "cookie", "galleta", "alfajor", "cheesecake", "pionono", "brownie", "mousse", "pan dulce", "rosca", "factura", "medialuna", "postre", "merengue", "pavlova")
NOT_DINNER = {"pasteleria", "postres", "helados", "panes", "bebidas", "mermeladas", "snacks", "picadas", "salsas"}
NOT_PLATE = ("chipa", "pan ", "pan de", "prepizza", "salsa ", "aderezo", "dip", "picada", "snack", "galleta", "medialuna", "factura", "tostado", "sandwich de miga", "palitos", "bolitas", "focaccia", "grisines", "bizcocho")


PLATE = ("tarta", "empanada", "pizza", "milanesa", "guiso", "sopa", "estofado", "cazuela", "pasta", "fideos", "ravioles", "noquis", "ñoquis", "lasagna", "lasana", "canelon", "risotto", "paella", "arroz", "wok", "salteado", "rellen", "pastel", "budin de", "tortilla", "revuelto", "omelette", "pollo", "carne", "pescado", "cerdo", "bondiola", "matambre", "asado", "caldo", "minestrone", "fideua", "fideuá")
NOT_PLATE = ("chipa", "pan ", "pan de", "prepizza", "salsa ", "aderezo", "dip ", "picada", "snack", "galleta", "medialuna", "factura", "tostado", "palitos", "bolitas", "focaccia", "grisines", "bizcocho", "muffin", "cupcake", "cookie")
STOP = {"para", "con", "una", "uno", "receta", "recetas", "cena", "rapida", "rápida", "vegetariana", "persona", "personas", "decime", "pasame", "quiero"}


def is_dinner(rec: dict[str, Any]) -> bool:
    title = fold(rec.get("title") or "")
    if title.startswith("salsa") or "salsa " in title or "galleta" in title or "muffin" in title or "torta" in title or "lotus" in title:
        return False
    if any(w in title for w in SWEET) or any(w in title for w in NOT_PLATE):
        return False
    if "al vapor" in title or "guia" in title:
        return False
    return any(w in title for w in PLATE)


def _query_score(title: str, query: str) -> float:
    words = [w for w in fold(query).split() if len(w) > 2 and w not in STOP]
    if not words:
        return 0
    return sum(1 for w in words if w in title) / len(words)


def looks_meat(rec: dict[str, Any]) -> bool:
    return not is_veg(rec)


ALIASES = {
    "zuccini": "zucchini",
    "zucchini": "calabacin",
    "zapallito": "calabacin",
    "calabacin": "calabacin",
    "garbanzos": "garbanzo",
    "huevos": "huevo",
    "queso": "queso",
}


def _have_names(have: list[str]) -> set[str]:
    names = set()
    for raw in have:
        name = ALIASES.get(fold(raw), canon_ingredient(raw))
        names.add(fold(name))
        names.add(fold(raw))
    return names


def _hits(ings: list[str], title: str, wanted: set[str], extra: str = "") -> set[str]:
    blob = " ".join(fold(i) for i in ings) + " " + title + " " + fold(extra)
    found = set()
    for w in wanted:
        if not w:
            continue
        alias = ALIASES.get(w, w)
        if w in blob or alias in blob or (w == "zucchini" and "calabacin" in blob):
            found.add(w)
    return found


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
    have_set = _have_names(have)
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
        if diet == "vegetarian" and not is_veg(rec):
            continue
        if diet == "vegan" and (not is_veg(rec) or any(w in fold(" ".join(rec.get("ingredients") or [])) for w in ("huevo", "queso", "leche", "manteca", "crema", "yogur"))):
            continue
        if diet == "meat" and is_veg(rec):
            continue
        if max_minutes and (rec.get("minutes") or 999) > max_minutes:
            continue
        tags = rec.get("tags") or []
        if meal == "postre" and "postre" not in tags:
            continue
        title_f = fold(rec.get("title") or "")
        qscore = _query_score(title_f, q) if q else 0
        if q and not have_set and qscore < 0.5 and q not in title_f:
            continue
        if meal in {"cena", "almuerzo"} and not is_dinner(rec):
            continue
        ings = rec.get("ingredients") or []
        if exclude_set and any(fold(i) in exclude_set for i in ings):
            continue
        hits = _hits(ings, title_f, have_set, " ".join(rec.get("amounts") or [])) if have_set else set()
        score = 1.0 + qscore * 8 + len(hits) * 6
        if have_set:
            score += len(hits) / max(len(have_set), 1) * 5
        if diet == "vegetarian":
            score += 1
        rec = {**rec, "_match": sorted(hits)}
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
    flag = "vegetariana" if is_veg(rec) else "con carne o pescado"
    own = " · tuya" if rec.get("custom") else ""
    match = rec.get("_match") or []
    shown = []
    for item in match:
        if item in {"zucchini", "calabacin"} and any(x in shown for x in ("zucchini", "calabacin")):
            continue
        shown.append(item)
    extra = f"\n   coincide: {', '.join(shown)}" if shown else ""
    return f"{index}. {rec.get('title')} ({mins} min, {flag}{own})\n   {ings}{extra}"


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
        f"{'vegetariana' if is_veg(rec) else 'no vegetariana'}\n\n"
        f"{label}:\n{ings}\n\n"
        f"{proc}{extra}"
    )
