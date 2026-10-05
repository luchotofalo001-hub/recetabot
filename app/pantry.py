from __future__ import annotations

import re
from typing import Any

from app.search import canon_ingredient, fold

UNITS = {
    "g": "g", "gr": "g", "grs": "g", "gramo": "g", "gramos": "g",
    "kg": "kg", "kilo": "kg", "kilos": "kg",
    "ml": "ml", "cc": "ml",
    "l": "l", "lt": "l", "litro": "l", "litros": "l",
    "un": "un", "u": "un", "unidad": "un", "unidades": "un",
    "cdita": "cdita", "cda": "cda", "cucharada": "cda", "cucharadas": "cda",
    "pizca": "pizca",
}


def _num(raw: str) -> float:
    raw = raw.replace(",", ".")
    if "/" in raw:
        a, b = raw.split("/", 1)
        return float(a) / float(b)
    return float(raw)


def parse_item(text: str) -> dict[str, Any] | None:
    clean = re.sub(r"^[\-\*\d\.\)\s]+", "", text.strip())
    clean = re.sub(r"\s+", " ", clean)
    if not clean:
        return None
    m = re.match(
        r"^(?:(\d+(?:[.,]\d+)?|\d+/\d+)\s+)?(?:(kg|kilos?|g|grs?|gramos|ml|cc|l|lt|litros?|unidades?|u|cditas?|cdas?|cucharadas?|pizca)\s+)?(?:de\s+)?(.+)$",
        clean,
        re.I,
    )
    if not m:
        return {"name": canon_ingredient(clean), "qty": None, "unit": None, "raw": clean}
    qty = _num(m.group(1)) if m.group(1) else None
    unit = UNITS.get((m.group(2) or "").lower()) if m.group(2) else None
    name = canon_ingredient(m.group(3).strip(" ."))
    if qty is None and unit is None:
        tail = re.match(r"^(.+?)\s+(\d+(?:[.,]\d+)?)\s*(kg|g|grs?|ml|cc|l|unidades?)?$", clean, re.I)
        if tail:
            name = canon_ingredient(tail.group(1))
            qty = _num(tail.group(2))
            unit = UNITS.get((tail.group(3) or "un").lower(), "un")
    return {"name": name, "qty": qty, "unit": unit or ("un" if qty else None), "raw": clean}


def parse_list(text: str) -> list[dict[str, Any]]:
    chunks = re.split(r"[\n,;]+", text)
    out = []
    for chunk in chunks:
        chunk = re.sub(r"^(tengo|hay|sum[aá]|agreg[aá]|cargar|stock)\s+", "", chunk.strip(), flags=re.I)
        item = parse_item(chunk)
        if item and item["name"]:
            out.append(item)
    return out


def to_base(qty: float, unit: str | None) -> tuple[float, str]:
    unit = unit or "un"
    if unit == "kg":
        return qty * 1000, "g"
    if unit == "l":
        return qty * 1000, "ml"
    return qty, unit


def format_qty(qty: float, unit: str | None) -> str:
    if qty is None:
        return ""
    shown = int(qty) if float(qty).is_integer() else round(qty, 2)
    return f"{shown} {unit or 'un'}"


def deduct(pantry: list[dict[str, Any]], amounts: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    notes = []
    by_name = {fold(p["name"]): p for p in pantry}
    for line in amounts:
        item = parse_item(line)
        if not item:
            continue
        key = fold(item["name"])
        stock = by_name.get(key)
        if not stock:
            notes.append(f"No estaba en la heladera: {item['name']}")
            continue
        if item["qty"] is None or stock.get("qty") is None:
            notes.append(f"No desconté cantidad de {item['name']} (faltaba número)")
            continue
        have_q, have_u = to_base(float(stock["qty"]), stock.get("unit"))
        need_q, need_u = to_base(float(item["qty"]), item.get("unit"))
        if have_u != need_u:
            notes.append(f"No desconté {item['name']}: unidades distintas ({stock.get('unit')} vs {item.get('unit')})")
            continue
        left = have_q - need_q
        if left <= 0:
            stock["qty"] = 0
            notes.append(f"Se acabó {item['name']}")
        else:
            if have_u == "g" and stock.get("unit") == "kg":
                stock["qty"] = round(left / 1000, 3)
            elif have_u == "ml" and stock.get("unit") == "l":
                stock["qty"] = round(left / 1000, 3)
            else:
                stock["qty"] = round(left, 2)
            notes.append(f"Quedan {format_qty(stock['qty'], stock.get('unit'))} de {item['name']}")
    return list(by_name.values()), notes
