from __future__ import annotations

import re

from app.extract import estimate_minutes, extract_ingredients, is_vegan, is_vegetarian

SECTION = re.compile(
    r"(t[ií]tulo|nombre|ingredientes|procedimiento|preparaci[oó]n|pasos)\s*[:\-]\s*",
    re.I,
)


def parse_custom_recipe(text: str) -> dict:
    clean = text.strip()
    parts = SECTION.split(clean)
    bucket = {"titulo": "", "ingredientes": "", "procedimiento": ""}
    if len(parts) >= 3:
        it = iter(parts[1:])
        for key, value in zip(it, it):
            k = key.lower()
            if k.startswith("t") or k.startswith("n"):
                bucket["titulo"] = value.strip()
            elif k.startswith("i"):
                bucket["ingredientes"] = value.strip()
            else:
                bucket["procedimiento"] = value.strip()
    title = bucket["titulo"] or clean.splitlines()[0][:80]
    procedure = bucket["procedimiento"] or clean
    extra = bucket["ingredientes"]
    amounts = []
    for line in re.split(r"[\n;]", extra):
        line = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
        if line:
            amounts.append(line)
    ingredients = extract_ingredients(title, f"{extra}\n{procedure}")
    return {
        "title": title.strip(" :-"),
        "category": "propia",
        "procedure": procedure.strip(),
        "ingredients": ingredients,
        "amounts": amounts,
        "minutes": estimate_minutes(procedure, title),
        "vegetarian": is_vegetarian(ingredients, title, "propia"),
        "vegan": is_vegan(ingredients, title, "propia"),
        "tags": ["plato", "propia"],
        "custom": True,
        "incomplete": len(procedure) < 80,
    }
