# -*- coding: utf-8 -*-
"""AI Chat for admin — Groq + PostgreSQL context. No /ai needed — just write."""
import logging, httpx
from datetime import datetime
from database.db import SessionLocal, AiConversation
from config import GROQ_API_KEY as GROQ_KEY

logger = logging.getLogger(__name__)
MAX_HISTORY = 20

SYSTEM_PROMPT = """You are an AI assistant for a lash extensions master. You are built into the Telegram bot @lashessoto4ka_bot and help the admin (salon owner) with her work.

Your capabilities:
- Help with schedule planning and workday optimization
- Tips on client communication
- Marketing and promotion ideas
- Workload analysis and improvement suggestions
- Pricing calculations, discounts, promotions
- Answering any business-related questions
- Being a friendly conversationalist

Context:
- - Booking statuses: pending -> confirmed -> completed | cancelled
- You talk to a MASTER, not a developer. Do NOT mention code, databases, or technical details.
- Reply briefly, friendly, in RUSSIAN. Be helpful and supportive.
- If you don't know the answer, say so honestly and suggest an alternative.
- The user is a woman who runs her own lash extension business."""

def _save(user_id, role, content):
    with SessionLocal() as db:
        db.add(AiConversation(user_id=user_id, role=role, content=content, created_at=datetime.utcnow().isoformat()))
        db.commit()

def _load(user_id):
    with SessionLocal() as db:
        rows = db.query(AiConversation).filter(AiConversation.user_id == user_id).order_by(AiConversation.created_at.desc()).limit(MAX_HISTORY).all()
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]

async def ask_groq(user_id: int, user_text: str) -> str:
    """Send user_text to Groq with conversation history, return response."""
    if not GROQ_KEY:
        return "Groq API key not configured."

    if not user_text.strip():
        return ""

    _save(user_id, "user", user_text)

    history = _load(user_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            )
            r.raise_for_status()
            reply = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = f"Error: {e}"

    _save(user_id, "assistant", reply)
    return reply

def clear_history(user_id: int) -> None:
    """Delete all conversation history for user."""
    with SessionLocal() as db:
        db.query(AiConversation).filter(AiConversation.user_id == user_id).delete()
        db.commit()
