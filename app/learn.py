"""Patrones de frases ya interpretadas por Gemini."""
from __future__ import annotations

import re
from typing import Any

from app.db import client
from app.extract import fold

_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def pattern_of(text: str) -> str:
    folded = fold(text)
    folded = _NUM.sub("{n}", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    return folded[:240]


def _numbers(text: str) -> list[str]:
    return _NUM.findall(text or "")


def _refill(parsed: dict[str, Any], text: str) -> dict[str, Any]:
    data = dict(parsed)
    nums = _numbers(text)
    items = data.get("pantry_items") or []
    for item, num in zip(items, nums):
        if isinstance(item, dict):
            item["qty"] = float(num.replace(",", "."))
    if nums and data.get("picks"):
        for pick, num in zip(data["picks"], nums):
            if isinstance(pick, dict):
                pick["option"] = int(float(num.replace(",", ".")))
    return data


def find_pattern(text: str) -> dict[str, Any] | None:
    pattern = pattern_of(text)
    if len(pattern) < 4:
        return None
    res = client().table("learned_phrases").select("parsed,hits").eq("pattern", pattern).limit(1).execute()
    if not res.data:
        return None
    row = res.data[0]
    client().table("learned_phrases").update({"hits": (row.get("hits") or 1) + 1}).eq("pattern", pattern).execute()
    parsed = _refill(row.get("parsed") or {}, text)
    parsed["_from_memory"] = True
    return parsed


def save_pattern(text: str, parsed: dict[str, Any]) -> None:
    intent = parsed.get("intent")
    if intent in {None, "other", "help"}:
        return
    pattern = pattern_of(text)
    if len(pattern) < 4:
        return
    clean = {k: v for k, v in parsed.items() if not k.startswith("_")}
    client().table("learned_phrases").upsert(
        {"pattern": pattern, "example": text[:300], "parsed": clean, "hits": 1},
        on_conflict="pattern",
    ).execute()
