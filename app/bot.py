from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.ai import parse_message
from app.db import (
    add_feedback,
    find_custom_by_name,
    get_state,
    insert_recipe,
    list_pantry,
    remove_pantry,
    save_pantry,
    save_state,
)
from app.pantry import deduct, format_qty, parse_item, parse_list
from app.parser import parse_custom_recipe
from app.quantities import fetch_amounts
from app.search import format_detail, format_option, search_slot

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
ALLOWED = {int(x) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip().isdigit()}


def tg(method: str, payload: dict) -> dict:
    with httpx.Client(timeout=30) as http:
        res = http.post(f"{API}/{method}", json=payload)
        res.raise_for_status()
        return res.json()


def send(chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> None:
    body: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "Markdown"}
    if buttons:
        body["reply_markup"] = {"inline_keyboard": buttons}
    try:
        tg("sendMessage", body)
    except httpx.HTTPStatusError:
        body.pop("parse_mode", None)
        tg("sendMessage", body)


def _brief(state: dict) -> str:
    slots = state.get("slots") or []
    lines = []
    for i, slot in enumerate(slots):
        opts = [f"{n+1}:{o.get('title')}" for n, o in enumerate(slot.get("options") or [])]
        lines.append(f"slot {i} {slot.get('label')}: " + ", ".join(opts))
    return "\n".join(lines)


def _buttons_for(slot: int, index: int) -> list[list[dict]]:
    return [[
        {"text": "Ver", "callback_data": f"see:{slot}:{index}"},
        {"text": "La hice", "callback_data": f"cook:{slot}:{index}"},
        {"text": "Me gustó", "callback_data": f"like:{slot}:{index}"},
        {"text": "No", "callback_data": f"fail:{slot}:{index}"},
    ]]


def _present(chat_id: int, state: dict) -> None:
    slots = state.get("slots") or []
    if not slots or not any(s.get("options") for s in slots):
        send(chat_id, "No encontré recetas con eso. Probá el nombre del plato, por ejemplo: recetas de tarta de verdura.")
        return
    for i, slot in enumerate(slots):
        send(chat_id, f"*{slot.get('label', 'Opciones')}*")
        for n, rec in enumerate(slot.get("options") or []):
            send(chat_id, format_option(n + 1, rec), _buttons_for(i, n))
    extra = [[{"text": "Otras opciones", "callback_data": "more"}]]
    if len(slots) > 1:
        extra.append([{"text": f"Otras {s.get('label', i)}", "callback_data": f"slot:{i}"} for i, s in enumerate(slots)][:3])
    send(chat_id, "Tocá Ver para las cantidades y el paso a paso.", extra)


def _have(chat_id: int, parsed: dict, previous: dict | None) -> list[str]:
    if parsed.get("ingredients_have"):
        return parsed["ingredients_have"]
    if parsed.get("use_pantry") is False:
        return (previous or {}).get("have") or []
    stock = list_pantry(chat_id)
    if stock:
        return [row["name"] for row in stock if row.get("qty") is None or float(row["qty"]) > 0]
    return (previous or {}).get("have") or []


def _pantry_text(chat_id: int) -> str:
    rows = list_pantry(chat_id)
    if not rows:
        return "La heladera está vacía. Mandame por ejemplo: tengo 6 huevos, 1 lechuga, 1 l de leche, 2 kg de papa."
    lines = ["Heladera:"]
    for row in rows:
        qty = format_qty(float(row["qty"]), row.get("unit")) if row.get("qty") is not None else "sin cantidad"
        lines.append(f"• {row['name']}: {qty}")
    return "\n".join(lines)


def _add_pantry(chat_id: int, text: str, parsed: dict) -> str:
    items = parsed.get("pantry_items") or []
    parsed_items = []
    for item in items:
        if item.get("name"):
            parsed_items.append({"name": item["name"], "qty": item.get("qty"), "unit": item.get("unit") or "un", "raw": item["name"]})
    if not parsed_items:
        parsed_items = parse_list(text)
    current = {row["name"]: row for row in list_pantry(chat_id)}
    for item in parsed_items:
        prev = current.get(item["name"])
        if prev and prev.get("qty") is not None and item.get("qty") is not None and (prev.get("unit") or "un") == (item.get("unit") or "un"):
            item["qty"] = float(prev["qty"]) + float(item["qty"])
        current[item["name"]] = item
    save_pantry(chat_id, list(current.values()))
    return "Actualicé la heladera.\n" + _pantry_text(chat_id)


def _remove_pantry(chat_id: int, text: str, parsed: dict) -> str:
    names = parsed.get("pantry_remove") or []
    if not names:
        names = [item["name"] for item in parse_list(text)]
    partial = parsed.get("pantry_items") or []
    current = {row["name"]: row for row in list_pantry(chat_id)}
    for item in partial:
        if not item.get("qty"):
            continue
        stock = current.get(item["name"])
        if stock and stock.get("qty") is not None:
            stock["qty"] = max(0, float(stock["qty"]) - float(item["qty"]))
    if names and not partial:
        remove_pantry(chat_id, names)
        for name in names:
            current.pop(name, None)
    save_pantry(chat_id, list(current.values()))
    return "Listo.\n" + _pantry_text(chat_id)


def _consume(chat_id: int, rec: dict) -> str:
    rec = with_amounts(rec)
    amounts = rec.get("amounts") or []
    if not amounts:
        return "La marqué como hecha. No desconté nada: esa receta no tiene cantidades."
    updated, notes = deduct(list_pantry(chat_id), amounts)
    save_pantry(chat_id, updated)
    detail = "\n".join(notes[:12]) if notes else "No encontré esos productos en la heladera."
    return "Desconté lo que pude:\n" + detail


def _run_search(chat_id: int, recipes, feedback, parsed, previous: dict | None, only_slot: int | None) -> dict:
    prev_slots = (previous or {}).get("slots") or []
    avoid = set(previous.get("seen") or []) if previous else set()
    slots_in = parsed.get("slots") or [{"diet": "any", "label": "cualquiera"}]
    if only_slot is not None and prev_slots:
        slots_in = [
            {"diet": s.get("diet", "any"), "label": s.get("label")}
            for s in prev_slots
        ]
    have = _have(chat_id, parsed, previous)
    built = []
    for idx, slot in enumerate(slots_in):
        if only_slot is not None and idx != only_slot and prev_slots:
            built.append(prev_slots[idx])
            continue
        options = search_slot(
            recipes,
            feedback,
            diet=slot.get("diet") or "any",
            have=have,
            exclude=parsed.get("ingredients_exclude") or [],
            max_minutes=parsed.get("max_minutes") if parsed.get("max_minutes") is not None else (previous or {}).get("max_minutes"),
            meal=parsed.get("meal") or (previous or {}).get("meal"),
            query=parsed.get("query") or (previous or {}).get("query"),
            avoid_ids=avoid,
            limit=3,
            allow_recent=bool(parsed.get("query")),
        )
        for opt in options:
            avoid.add(opt["id"])
        built.append({"diet": slot.get("diet") or "any", "label": slot.get("label") or "opción", "options": options})
    return {
        "slots": built,
        "seen": list(avoid)[-80:],
        "have": have,
        "max_minutes": parsed.get("max_minutes", (previous or {}).get("max_minutes")),
        "query": parsed.get("query") or (previous or {}).get("query"),
    }


def _render(state: dict) -> str:
    chunks = []
    if not state.get("slots"):
        return "No encontré recetas con esos filtros. Probá con menos ingredientes o sin el límite de tiempo."
    for slot in state["slots"]:
        lines = [f"*{slot.get('label', 'Opciones')}*"]
        opts = slot.get("options") or []
        if not opts:
            lines.append("No hay más con ese filtro.")
        for n, rec in enumerate(opts, start=1):
            lines.append(format_option(n, rec))
        chunks.append("\n".join(lines))
    chunks.append("Rápida = 45 min o menos de estimado (cocción + prep, sin reposos de un día).")
    return "\n\n".join(chunks)


def with_amounts(rec: dict) -> dict:
    if rec.get("amounts"):
        return rec
    amounts = fetch_amounts(rec.get("url") or "")
    if not amounts:
        return rec
    rec = {**rec, "amounts": amounts}
    if rec.get("id"):
        try:
            from app.db import client
            client().table("recipes").update({"amounts": amounts}).eq("id", rec["id"]).execute()
        except Exception:
            pass
    return rec


def _option(state: dict, slot: int, index: int) -> dict | None:
    slots = state.get("slots") or []
    if slot >= len(slots):
        return None
    opts = slots[slot].get("options") or []
    if index >= len(opts):
        return None
    return opts[index]


def _apply_pick(chat_id: int, state: dict, slot: int, index: int, kind: str) -> str:
    rec = _option(state, slot, index)
    if not rec:
        return f"No está la {index + 1} del grupo {slot + 1}."
    label = f"{slot + 1}.{index + 1} {rec.get('title')}"
    if kind == "detail":
        return format_detail(with_amounts(rec))
    add_feedback(chat_id, rec["id"], kind)
    if kind == "cooked":
        return f"{label}: hecha, no vuelve por 2 días.\n" + _consume(chat_id, rec)
    if kind == "liked":
        return f"{label}: me gustó, la priorizo."
    return f"{label}: no funcionó, no la muestro más."


def _picks_from_text(text: str) -> list[dict]:
    low = text.lower()
    slot_words = {"primer": 0, "1er": 0, "segund": 1, "2do": 1, "tercer": 2}
    picks = []
    for chunk in re.split(r"\s+y\s+|,\s*", low):
        opt = re.search(r"\bla\s+(\d)\b", chunk)
        if not opt:
            continue
        slot = 0
        for word, idx in slot_words.items():
            if word in chunk:
                slot = idx
        kind = "cooked"
        if "no funcion" in chunk or "no me gust" in chunk:
            kind = "failed"
        elif "gust" in chunk or "like" in chunk:
            kind = "liked"
        elif "ver" in chunk or "pasame" in chunk:
            kind = "detail"
        picks.append({"slot": slot, "option": int(opt.group(1)), "action": kind})
    return picks
    slots = state.get("slots") or []
    if slot >= len(slots):
        return None
    opts = slots[slot].get("options") or []
    if index >= len(opts):
        return None
    return opts[index]


def handle_text(chat_id: int, text: str, recipes: list[dict], feedback: list[dict]) -> None:
    state = get_state(chat_id)
    if text.lower().startswith("/start"):
        send(chat_id, "Decime para cuántos y si alguno es vegetariano. La heladera se carga con: tengo 6 huevos, 1 lechuga, 1 l de leche. /heladera la muestra.")
        return
    if text.lower().startswith("/heladera"):
        send(chat_id, _pantry_text(chat_id))
        return
    if text.lower().startswith("/cargar"):
        text = text.split(" ", 1)[1] if " " in text else text
        parsed = {"intent": "save"}
    else:
        parsed = parse_message(text, _brief(state))
    intent = parsed.get("intent") or "search"
    if intent == "pantry_list":
        send(chat_id, _pantry_text(chat_id))
        return
    if intent == "pantry_add":
        send(chat_id, _add_pantry(chat_id, text, parsed))
        return
    if intent == "pantry_remove":
        send(chat_id, _remove_pantry(chat_id, text, parsed))
        return
    if intent == "help":
        send(chat_id, "Pedime recetas con ingredientes, marcá La hice / Me gustó / No funcionó, o /cargar seguido del texto de una receta tuya.")
        return
    if intent == "save" or text.lower().startswith("/cargar"):
        row = parse_custom_recipe(text)
        saved = insert_recipe({**row, "external_id": None, "url": None})
        recipes.append(saved)
        send(chat_id, f"Guardé *{row['title']}* ({row['minutes']} min). Pedime «cómo es mi receta de {row['title']}».")
        return
    if intent == "show_mine":
        name = parsed.get("named_recipe") or parsed.get("query") or text
        found = find_custom_by_name(str(name)[:40])
        if not found:
            send(chat_id, "No tengo una receta tuya con ese nombre.")
            return
        send(chat_id, format_detail(with_amounts(found[0])))
        return
    picks = parsed.get("picks") or []
    if not picks and any(w in text.lower() for w in ("del primero", "del segundo", "la 1", "la 2", "la 3")):
        picks = _picks_from_text(text)
    if picks:
        notes = [_apply_pick(chat_id, state, int(p.get("slot") or 0), int(p.get("option") or 1) - 1, p.get("action") or "cooked") for p in picks]
        send(chat_id, "\n\n".join(notes)[:4000])
        return
    if intent in {"cooked", "liked", "failed", "detail"} and parsed.get("option_index"):
        slot = int(parsed.get("slot_index") or 0)
        index = int(parsed["option_index"]) - 1
        rec = _option(state, slot, index)
        if not rec:
            send(chat_id, "No veo esa opción en lo último que te pasé.")
            return
        if intent == "detail":
            send(chat_id, format_detail(with_amounts(rec)))
            return
        kind = {"cooked": "cooked", "liked": "liked", "failed": "failed"}[intent]
        add_feedback(chat_id, rec["id"], kind)
        feedback.append({"recipe_id": rec["id"], "kind": kind, "created_at": "2099-01-01T00:00:00+00:00"})
        msg = {"cooked": "Anotado. No te la vuelvo a mostrar por 2 días.\n" + _consume(chat_id, rec), "liked": "La voy a priorizar.", "failed": "Listo, esa no aparece más salvo que la pidas por nombre."}[intent]
        send(chat_id, msg)
        return
    only = parsed.get("slot_index") if intent == "replace" else None
    if intent == "more":
        only = None
        parsed = {**parsed, "ingredients_have": state.get("have") or [], "max_minutes": state.get("max_minutes"), "slots": [
            {"diet": s.get("diet"), "label": s.get("label")} for s in state.get("slots") or parsed.get("slots") or []
        ]}
    new_state = _run_search(chat_id, recipes, feedback, parsed, state if intent in {"more", "replace"} else None, only if intent == "replace" else None)
    save_state(chat_id, new_state)
    _present(chat_id, new_state)


def handle_callback(chat_id: int, data: str, recipes: list[dict], feedback: list[dict]) -> None:
    state = get_state(chat_id)
    if data == "more":
        parsed = {"intent": "more", "slots": [{"diet": s.get("diet"), "label": s.get("label")} for s in state.get("slots") or []], "ingredients_have": state.get("have") or [], "max_minutes": state.get("max_minutes")}
        new_state = _run_search(chat_id, recipes, feedback, parsed, state, None)
        save_state(chat_id, new_state)
        _present(chat_id, new_state)
        return
    kind, *rest = data.split(":")
    if kind == "slot":
        slot = int(rest[0])
        parsed = {"intent": "replace", "slot_index": slot, "ingredients_have": state.get("have") or [], "max_minutes": state.get("max_minutes"), "slots": []}
        new_state = _run_search(chat_id, recipes, feedback, parsed, state, slot)
        save_state(chat_id, new_state)
        _present(chat_id, new_state)
        return
    slot, index = int(rest[0]), int(rest[1])
    rec = _option(state, slot, index)
    if not rec:
        send(chat_id, "Esa opción ya no está en el último mensaje.")
        return
    if kind == "see":
        send(chat_id, format_detail(with_amounts(rec)))
        return
    mapped = {"cook": "cooked", "like": "liked", "fail": "failed"}[kind]
    add_feedback(chat_id, rec["id"], mapped)
    extra = "\n" + _consume(chat_id, rec) if mapped == "cooked" else ""
    send(chat_id, "Anotado." + extra)


def allowed(chat_id: int) -> bool:
    return not ALLOWED or chat_id in ALLOWED
