from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.bot import allowed, handle_callback, handle_text, tg
from app.db import fetch_feedback, fetch_recipes

app = FastAPI()
RECIPES: list[dict] = []
SEEN: set[int] = set()


@app.on_event("startup")
def startup() -> None:
    global RECIPES
    if os.environ.get("SUPABASE_URL"):
        RECIPES = fetch_recipes()
    secret = os.environ.get("WEBHOOK_SECRET", "recetabot")
    base = os.environ.get("PUBLIC_URL", "").rstrip("/")
    if base and os.environ.get("TELEGRAM_TOKEN"):
        tg("setWebhook", {"url": f"{base}/webhook/{secret}"})


@app.get("/health")
def health() -> dict:
    return {"ok": True, "recipes": len(RECIPES)}


@app.post("/webhook/{secret}")
async def webhook(secret: str, request: Request) -> JSONResponse:
    if secret != os.environ.get("WEBHOOK_SECRET", "recetabot"):
        return JSONResponse({"ok": False}, status_code=403)
    update = await request.json()
    update_id = update.get("update_id")
    if update_id in SEEN:
        return JSONResponse({"ok": True})
    SEEN.add(update_id)
    if len(SEEN) > 500:
        SEEN.clear()
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        if not allowed(chat_id):
            return JSONResponse({"ok": True})
        text = msg.get("text") or ""
        if text:
            handle_text(chat_id, text, RECIPES, fetch_feedback(chat_id))
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
        if allowed(chat_id):
            handle_callback(chat_id, cq.get("data") or "", RECIPES, fetch_feedback(chat_id))
    return JSONResponse({"ok": True})
