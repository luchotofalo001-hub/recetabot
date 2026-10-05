from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client, create_client

_client: Client | None = None


def client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def fetch_recipes() -> list[dict[str, Any]]:
    sb = client()
    rows: list[dict[str, Any]] = []
    start = 0
    page = 1000
    while True:
        res = (
            sb.table("recipes")
            .select(
                "id,title,category,url,procedure,ingredients,amounts,minutes,vegetarian,vegan,tags,custom,incomplete"
            )
            .range(start, start + page - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page
    return rows


def fetch_feedback(chat_id: int) -> list[dict[str, Any]]:
    since = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    res = (
        client()
        .table("feedback")
        .select("recipe_id,kind,created_at")
        .eq("chat_id", chat_id)
        .gte("created_at", since)
        .execute()
    )
    return res.data or []


def add_feedback(chat_id: int, recipe_id: str, kind: str) -> None:
    client().table("feedback").insert(
        {"chat_id": chat_id, "recipe_id": recipe_id, "kind": kind}
    ).execute()


def get_state(chat_id: int) -> dict[str, Any]:
    res = client().table("chat_state").select("payload").eq("chat_id", chat_id).execute()
    if res.data:
        return res.data[0].get("payload") or {}
    return {}


def save_state(chat_id: int, payload: dict[str, Any]) -> None:
    client().table("chat_state").upsert(
        {"chat_id": chat_id, "payload": payload, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).execute()


def insert_recipe(row: dict[str, Any]) -> dict[str, Any]:
    res = client().table("recipes").insert(row).execute()
    return (res.data or [row])[0]


def find_custom_by_name(query: str) -> list[dict[str, Any]]:
    res = (
        client()
        .table("recipes")
        .select("id,title,category,url,procedure,ingredients,amounts,minutes,vegetarian,vegan,tags,custom,incomplete")
        .eq("custom", True)
        .ilike("title", f"%{query}%")
        .limit(5)
        .execute()
    )
    return res.data or []


def list_pantry(chat_id: int) -> list[dict[str, Any]]:
    res = (
        client()
        .table("pantry")
        .select("name,qty,unit")
        .eq("chat_id", chat_id)
        .order("name")
        .execute()
    )
    return res.data or []


def save_pantry(chat_id: int, items: list[dict[str, Any]]) -> None:
    sb = client()
    for item in items:
        if item.get("qty") == 0:
            sb.table("pantry").delete().eq("chat_id", chat_id).eq("name", item["name"]).execute()
            continue
        sb.table("pantry").upsert(
            {
                "chat_id": chat_id,
                "name": item["name"],
                "qty": item.get("qty"),
                "unit": item.get("unit"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="chat_id,name",
        ).execute()


def remove_pantry(chat_id: int, names: list[str]) -> list[str]:
    sb = client()
    removed = []
    for name in names:
        sb.table("pantry").delete().eq("chat_id", chat_id).ilike("name", name).execute()
        removed.append(name)
    return removed
    res = (
        client()
        .table("recipes")
        .select("id,title,category,url,procedure,ingredients,amounts,minutes,vegetarian,vegan,tags,custom,incomplete")
        .eq("custom", True)
        .ilike("title", f"%{query}%")
        .limit(5)
        .execute()
    )
    return res.data or []
