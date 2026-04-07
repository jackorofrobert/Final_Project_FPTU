"""
Translate long text to English using Google AI Studio (Gemini) with chunked requests.
"""
import asyncio
import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

GEMINI_REST_BASE = "https://generativelanguage.googleapis.com/v1beta"
MAX_CHUNKS_HARD_CAP = 80
URL_PATTERN = re.compile(r"(https?://[^\s<>\"]+|www\.[^\s<>\"]+)", re.IGNORECASE)


def _resolve_google_ai_keys() -> list[str]:
    """
    Resolve API keys from settings.
    Supports:
    - GOOGLE_AI_API_KEYS as JSON array string: ["k1","k2"]
    - GOOGLE_AI_API_KEYS as comma-separated string: k1,k2
    - fallback GOOGLE_AI_API_KEY
    """
    keys: list[str] = []
    raw = (settings.GOOGLE_AI_API_KEYS or "").strip()
    if raw:
        parsed: Any = None
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
        if isinstance(parsed, list):
            keys.extend(str(v).strip() for v in parsed if str(v).strip())
        else:
            keys.extend(part.strip() for part in raw.split(",") if part.strip())

    single = (settings.GOOGLE_AI_API_KEY or "").strip()
    if single:
        keys.append(single)

    # Keep order, remove duplicates
    deduped: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _split_oversized_segment(segment: str, max_chars: int) -> list[str]:
    """Split a segment that exceeds max_chars, preferring spaces."""
    if len(segment) <= max_chars:
        return [segment]
    out: list[str] = []
    rest = segment
    while len(rest) > max_chars:
        window = rest[:max_chars]
        break_at = window.rfind(" ")
        if break_at > max_chars // 3:
            piece = rest[:break_at]
            rest = rest[break_at:].lstrip()
        else:
            piece = rest[:max_chars]
            rest = rest[max_chars:]
        if piece:
            out.append(piece)
    if rest:
        out.append(rest)
    return out


def _mask_urls(text: str) -> tuple[str, dict[str, str]]:
    """
    Replace URLs with deterministic placeholders so translation won't alter them.
    """
    if not text:
        return text, {}

    index = 0
    placeholders: dict[str, str] = {}

    def replacer(match: re.Match[str]) -> str:
        nonlocal index
        original = match.group(0)
        token = f"__URL_{index}__"
        placeholders[token] = original
        index += 1
        return token

    return URL_PATTERN.sub(replacer, text), placeholders


def _unmask_urls(text: str, placeholders: dict[str, str]) -> str:
    """Restore URL placeholders back to original links."""
    restored = text or ""
    for token, original in placeholders.items():
        restored = restored.replace(token, original)
    return restored


def chunk_text_for_translation(text: str, max_chars: int) -> list[str]:
    """
    Split text into chunks under max_chars, keeping paragraph boundaries when possible.
    """
    text = text or ""
    if not text.strip():
        return []

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

    for para in paragraphs:
        para = para.strip("\n")
        if not para:
            flush()
            continue

        if len(para) > max_chars:
            flush()
            for piece in _split_oversized_segment(para, max_chars):
                chunks.append(piece)
            continue

        need = len(para) + (2 if current else 0)
        if current_len + need <= max_chars:
            current.append(para)
            current_len += need
        else:
            flush()
            current = [para]
            current_len = len(para)

    flush()
    return chunks


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        reason = payload.get("promptFeedback") or {}
        raise ValueError(f"No translation returned: {reason}")
    first = candidates[0]
    fr = first.get("finishReason") or ""
    if fr and fr not in ("STOP", "MAX_TOKENS"):
        raise ValueError(f"Translation blocked or incomplete: finishReason={fr}")
    content = first.get("content") or {}
    parts = content.get("parts") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict))


async def _translate_one_chunk(
    client: httpx.AsyncClient,
    api_keys: list[str],
    model: str,
    chunk: str,
    chunk_index: int,
    total_chunks: int,
) -> str:
    prompt = (
        "You are a professional translator. Translate the following text to clear, natural English.\n"
        "Rules:\n"
        "- Output ONLY the English translation, no title, no quotes, no explanation.\n"
        "- Preserve structure: paragraphs, line breaks, bullet lists, and numbering as much as possible.\n"
        "- Keep any token matching __URL_<number>__ exactly unchanged.\n"
        "- This is part {idx} of {total} of a longer document; translate only this part.\n\n"
        "---\n{chunk}\n---"
    ).format(idx=chunk_index + 1, total=total_chunks, chunk=chunk)

    url = f"{GEMINI_REST_BASE}/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        },
    }
    attempts = len(api_keys)
    start_idx = chunk_index % attempts
    errors: list[str] = []

    for offset in range(attempts):
        key_index = (start_idx + offset) % attempts
        api_key = api_keys[key_index]
        response = await client.post(
            url,
            params={"key": api_key},
            json=body,
            timeout=httpx.Timeout(120.0, connect=30.0),
        )
        try:
            response.raise_for_status()
            data = response.json()
            return _extract_gemini_text(data).strip()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                err = exc.response.json()
                detail = (err.get("error") or {}).get("message") or str(err)
            except Exception:
                detail = exc.response.text or str(exc)
            errors.append(f"key#{key_index + 1}: {detail}")
            continue

    raise ValueError(f"Gemini API error (all keys failed): {' | '.join(errors)}")


async def translate_to_english(text: str) -> dict[str, Any]:
    """
    Translate full text to English using Gemini, chunking when needed.
    Returns dict with translated_text, chunk_count, source_chars, model.
    """
    api_keys = _resolve_google_ai_keys()
    if not api_keys:
        raise ValueError(
            "Google AI key is not configured (set GOOGLE_AI_API_KEY or GOOGLE_AI_API_KEYS)"
        )

    model = (settings.GEMINI_TRANSLATION_MODEL or "gemini-2.0-flash").strip()
    max_chars = max(512, min(settings.TRANSLATION_CHUNK_MAX_CHARS, 32000))

    source_text = text or ""
    source_chars = len(source_text)
    if source_chars > settings.TRANSLATION_MAX_INPUT_CHARS:
        raise ValueError(
            f"Text too long (max {settings.TRANSLATION_MAX_INPUT_CHARS} characters)"
        )

    masked_text, placeholders = _mask_urls(source_text)
    chunks = chunk_text_for_translation(masked_text, max_chars)
    if not chunks:
        return {
            "translated_text": "",
            "chunk_count": 0,
            "source_chars": source_chars,
            "model": model,
            "urls_preserved_count": len(placeholders),
        }

    if len(chunks) > MAX_CHUNKS_HARD_CAP:
        raise ValueError(
            f"Content would require {len(chunks)} API chunks; limit is {MAX_CHUNKS_HARD_CAP}. "
            "Try a shorter email or increase chunk size in settings."
        )

    logger.info(
        "Gemini translation: model=%s chunks=%s max_chunk_chars=%s source_chars=%s keys=%s",
        model,
        len(chunks),
        max_chars,
        source_chars,
        len(api_keys),
    )

    translated_parts: list[str] = []
    async with httpx.AsyncClient() as client:
        for i, chunk in enumerate(chunks):
            part = await _translate_one_chunk(
                client, api_keys, model, chunk, i, len(chunks)
            )
            translated_parts.append(part)
            if i < len(chunks) - 1:
                await asyncio.sleep(settings.TRANSLATION_CHUNK_DELAY_SECONDS)

    # Rejoin with double newline to mirror paragraph splits where possible
    translated_text = _unmask_urls("\n\n".join(translated_parts), placeholders)
    return {
        "translated_text": translated_text,
        "chunk_count": len(chunks),
        "source_chars": source_chars,
        "model": model,
        "urls_preserved_count": len(placeholders),
    }
