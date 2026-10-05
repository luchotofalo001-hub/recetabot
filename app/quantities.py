from __future__ import annotations

import re

import httpx

def public_url(url: str) -> str:
    url = (url or "").strip()
    url = url.replace("://www.", "://")
    return url.replace("/recetas/", "/")


def _text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>|<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|li|h1|h2|h3|div)>", "\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&", "&", html)
    html = re.sub(r"[ \t]+", " ", html)
    return re.sub(r"\n{2,}", "\n", html)


def fetch_amounts(url: str) -> list[str]:
    if not url:
        return []
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as http:
            res = http.get(public_url(url), headers={"User-Agent": "recetabot/1.0"})
            res.raise_for_status()
            body = _text(res.text)
    except Exception:
        return []
    low = body.lower()
    start = low.find("ingredientes")
    if start < 0:
        return []
    chunk = body[start:start + 1800]
    end = re.search(r"\n\s*preparaci[oó]n|\n\s*procedimiento", chunk, re.I)
    if end:
        chunk = chunk[:end.start()]
    lines = []
    for raw in chunk.splitlines():
        line = raw.strip(" -*•\t")
        if not line or line.lower() in {"ingredientes", "preparación", "procedimiento"}:
            continue
        if len(line) > 90:
            continue
        lines.append(line)
    return lines[:40]
