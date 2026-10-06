from __future__ import annotations

import json
import os
import re
from typing import Any

from app.learn import find_pattern, save_pattern

SYSTEM = """Sos el interprete de un bot de recetas. No inventes recetas ni ingredientes de platos.
Solo convertí el mensaje del usuario en JSON de filtros. Respondé únicamente JSON válido.
Esquema:
{
  "intent": "search|more|replace|detail|cooked|liked|failed|save|show_mine|pantry_add|pantry_remove|pantry_list|help|other",
  "slots": [{"diet": "any|vegetarian|vegan|meat", "label": "texto corto"}],
  "ingredients_have": ["papa"],
  "ingredients_exclude": [],
  "max_minutes": null,
  "meal": null,
  "query": null,
  "slot_index": null,
  "option_index": null,
  "named_recipe": null,
  "picks": [{"slot": 0, "option": 1, "action": "cooked"}],
  "pantry_items": [{"name": "lechuga", "qty": 1, "unit": "un"}],
  "pantry_remove": ["lechuga"],
  "use_pantry": true
}
Reglas:
- "rápida", "rapido", "cena express", "en un rato" => max_minutes 45.
- "cena para 2, una vegetariana" => dos slots: uno vegetarian y otro any. Nunca repitas el mismo slot.
- "cena" => meal cena. No postres.
- "con huevo y milanesa" => ingredients_have, no es una dieta. Si nombra milanesa, carne o pollo, no fuerces vegetarian.
- "otras", "otras opciones", "ninguna" => intent more.
- Si quiere conservar una opción y cambiar otra, intent replace, slot_index de la que hay que cambiar (0-based) y option_index de la que se queda si la nombra.
- "voy a hacer la 1 del primero y la 3 del segundo" => picks, slot 0-based, option 1-based, action cooked.
- "la 1 del primero me gustó y la 3 del segundo no funcionó" => dos picks, actions liked y failed.
- Cada pick es independiente. No juntes las dos recetas en una sola.
- "cómo es mi receta de X" => intent show_mine, named_recipe X.
- Si pega una receta para guardar (título, ingredientes, pasos) => intent save.
- Si dice qué hay en casa, "tengo", "sumá", "agregá a la heladera" => pantry_add y pantry_items con cantidad y unidad si las dijo.
- "saca", "se pudrió", "tiré", "no hay más" => pantry_remove. Si dice una cantidad, pantry_add con qty negativa no: pantry_remove y pantry_items con la cantidad a restar.
- "qué tengo", "mostrá la heladera" => pantry_list.
- use_pantry true salvo que diga "sin mirar la heladera" o liste ingredientes solo para esta búsqueda.
- No incluyas texto fuera del JSON.
"""


def _fallback(text: str) -> dict[str, Any]:
    t = text.lower()
    intent = "search"
    if any(w in t for w in ("otra", "otras", "ninguna", "no me convence")):
        intent = "more"
    if "no funcion" in t or "no me salió" in t or "no me salio" in t:
        intent = "failed"
    elif "me gust" in t or "estuvo buena" in t or "riquísima" in t or "riquisima" in t:
        intent = "liked"
    elif "la hice" in t or "ya la hice" in t or "cocinamos" in t:
        intent = "cooked"
    elif "mi receta" in t or "como es mi" in t or "cómo es mi" in t:
        intent = "show_mine"
    elif "heladera" in t or "qué tengo" in t or "que tengo" in t:
        intent = "pantry_list"
    elif any(w in t for w in ("se pudri", "sacá", "saca ", "tiré", "tire la", "no hay más")):
        intent = "pantry_remove"
    elif t.startswith("tengo ") or "sumá" in t or "suma " in t:
        intent = "pantry_add"
    slots = []
    if "vegetarian" in t:
        slots.append({"diet": "vegetarian", "label": "vegetariana"})
    if "vegan" in t:
        slots.append({"diet": "vegan", "label": "vegana"})
    if re.search(r"\b2 personas\b|\bdos personas\b", t) and len(slots) < 2:
        slots.append({"diet": "any", "label": "cualquiera"})
    if not slots:
        slots = [{"diet": "any", "label": "cualquiera"}]
    max_minutes = 45 if any(w in t for w in ("rapid", "rápid", "express", "en 30", "en 40", "menos de 45")) else None
    return {
        "intent": intent,
        "slots": slots,
        "ingredients_have": [],
        "ingredients_exclude": [],
        "max_minutes": max_minutes,
        "meal": "cena" if "cena" in t else None,
        "query": None,
        "slot_index": None,
        "option_index": None,
        "named_recipe": None,
        "pantry_items": [],
        "pantry_remove": [],
        "use_pantry": True,
    }


def normalize(text: str, parsed: dict[str, Any]) -> dict[str, Any]:
    t = text.lower()
    people = 1
    m = re.search(r"para\s+(\d)|(\d)\s+personas|dos personas", t)
    if m:
        people = int(m.group(1) or m.group(2) or 2)
    meat_words = ("milanesa", "carne", "pollo", "cerdo", "pescado", "higado", "hígado", "molleja")
    wants_veg = "vegetarian" in t and not any(w in t for w in meat_words)
    slots = []
    if wants_veg:
        slots.append({"diet": "vegetarian", "label": "vegetariana"})
    if people > len(slots):
        slots.append({"diet": "any", "label": "la otra" if slots else "cena"})
    while len(slots) < people and len(slots) < 4:
        slots.append({"diet": "any", "label": f"persona {len(slots) + 1}"})
    if "vegetarian" in t or "para 2" in t or "para dos" in t or re.search(r"\d\s+personas", t):
        parsed["slots"] = slots[: max(people, 1)]
    if "cena" in t or "almuerzo" in t:
        parsed["meal"] = "cena" if "cena" in t else "almuerzo"
    if any(w in t for w in ("rapid", "rápid")):
        parsed["max_minutes"] = 45
    dish = re.search(r"(?:recetas?|platos?|ideas?)\s+de\s+(.+)", t)
    with_ings = re.search(r"(?:recetas?|platos?)\s+con\s+(.+)", t)
    if with_ings:
        parts = re.split(r",|\by\b", with_ings.group(1))
        parsed["ingredients_have"] = [p.strip(" .") for p in parts if p.strip(" .")]
        parsed["query"] = None
        parsed["slots"] = [{"diet": "any", "label": "con lo que pediste"}]
        parsed["meal"] = None
    elif dish:
        q = re.split(r"\b(para|con|rapida|rápida|vegetariana|cena)\b", dish.group(1))[0].strip(" .")
        if q:
            parsed["query"] = q
            parsed["slots"] = [{"diet": "vegetarian" if wants_veg else "any", "label": q}]
            if "cena" not in t:
                parsed["meal"] = None
    elif not parsed.get("query") and not any(w in t for w in ("cena", "almuerzo", "heladera", "tengo")):
        parsed["query"] = t.strip()[:80]
    return parsed


def parse_message(text: str, state_brief: str = "") -> dict[str, Any]:
    remembered = None
    try:
        remembered = find_pattern(text)
    except Exception:
        remembered = None
    if remembered:
        return normalize(text, remembered)
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return normalize(text, _fallback(text))
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    prompt = SYSTEM + "\nContexto de opciones ya mostradas:\n" + (state_brief or "ninguno") + "\nMensaje:\n" + text
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    try:
        with httpx.Client(timeout=20) as http:
            res = http.post(url, json=body)
            res.raise_for_status()
            data = res.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw)
        if "intent" not in parsed:
            raise ValueError("sin intent")
        parsed.setdefault("slots", [{"diet": "any", "label": "cualquiera"}])
        try:
            save_pattern(text, parsed)
            parsed["_learned"] = True
        except Exception:
            pass
        return normalize(text, parsed)
    except Exception:
        return normalize(text, _fallback(text))
