"""
RAG (Retrieval-Augmented Generation) module for the AI Training Assistant.
Uses lightweight keyword-based retrieval against training_knowledge.py.
Reuses the existing Anthropic client from ai.py — no new dependencies.
"""
from __future__ import annotations

import re
from typing import Optional

import ai
import training_knowledge as kb

# ── Retrieval ──────────────────────────────────────────────────────────────────

_STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "of", "to", "and", "or",
    "for", "with", "do", "i", "my", "me", "how", "what", "why", "when",
    "should", "can", "could", "would", "will", "are", "be", "this", "that",
    "if", "not", "any", "by", "at", "as", "from", "was", "were", "has",
    "have", "had", "but", "so", "about", "some", "more", "which", "get",
    "much", "reduce", "increase", "improve", "help",
}


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z]+", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}


def _score(chunk: dict, question_tokens: set[str]) -> float:
    """
    Score a knowledge chunk against the question.
    Tag matches are weighted higher than content matches.
    """
    tag_tokens: set[str] = set()
    for tag in chunk.get("tags", []):
        tag_tokens |= _tokenize(tag)

    content_tokens = _tokenize(chunk["content"] + " " + chunk["title"] + " " + chunk["section"])

    tag_hits = len(question_tokens & tag_tokens)
    content_hits = len(question_tokens & content_tokens)
    return tag_hits * 3.0 + content_hits * 1.0


def retrieve(question: str, top_k: int = 3) -> list[dict]:
    """Return the top_k most relevant knowledge chunks for the question."""
    q_tokens = _tokenize(question)
    if not q_tokens:
        return kb.KNOWLEDGE[:top_k]

    scored = sorted(
        ((chunk, _score(chunk, q_tokens)) for chunk in kb.KNOWLEDGE),
        key=lambda x: x[1],
        reverse=True,
    )
    # Include chunks with at least 1 hit; fall back to top_k regardless
    filtered = [c for c, s in scored if s > 0]
    return (filtered or [c for c, _ in scored])[:top_k]


# ── Template Answer (no-LLM fallback) ─────────────────────────────────────────

def _template_answer(question: str, chunks: list[dict], shift_context: dict) -> str:
    """Build a plain-text answer from retrieved chunks when LLM is unavailable."""
    if not chunks:
        return (
            "The training knowledge base does not contain specific information "
            "about this topic. Please consult your site supervisor or equipment manual."
        )
    parts = [
        f"Based on operator training guidance:\n",
    ]
    for chunk in chunks[:2]:
        parts.append(f"**{chunk['title']}**\n{chunk['content']}\n")

    # Personalise with shift context if available
    ctx_lines = _shift_context_summary(shift_context)
    if ctx_lines:
        parts.append(f"\n*Current shift context: {ctx_lines}*")

    return "\n".join(parts)


def _shift_context_summary(ctx: dict) -> str:
    if not ctx:
        return ""
    notes = []
    anom = ctx.get("anomaly", {})
    if anom.get("flag") and anom.get("type") == "excess_idle":
        notes.append(f"idle time currently flagged ({anom.get('current', '?')} min)")
    safety = ctx.get("safety", {})
    if safety.get("level") in ("WARNING", "CRITICAL"):
        notes.append(f"safety level {safety['level']}")
    if ctx.get("weather") in ("rain", "heat"):
        notes.append(f"weather: {ctx['weather']}")
    return ", ".join(notes)


# ── LLM Answer ────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are an AI Training Assistant for heavy equipment operators.
Answer questions about excavator operation, safety, maintenance, and productivity.
Use ONLY the provided documentation chunks — do not invent machine specifications or safety thresholds.
If the documentation does not cover the question, explicitly say so.
Be concise and practical. Use numbered lists where appropriate.
Do not fabricate citations, manual names, or page numbers."""


def _build_prompt(question: str, chunks: list[dict], shift_context: dict) -> str:
    ctx_summary = _shift_context_summary(shift_context)
    parts = []

    if ctx_summary:
        parts.append(f"[Operator Shift Context: {ctx_summary}]\n")

    parts.append("Retrieved Documentation:\n")
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] {chunk['title']} — {chunk['section']}\n"
            f"{chunk['content']}\n"
        )

    parts.append(f"\nOperator Question: {question}")
    return "\n".join(parts)


# ── Public API ─────────────────────────────────────────────────────────────────

def answer(question: str, shift_context: Optional[dict] = None, state: Optional[dict] = None) -> dict:
    """
    Main RAG entry point.
    Returns: { answer, sources, source_type, grounded }
    """
    if shift_context is None:
        shift_context = {}

    # Merge live state into context for personalisation
    live_ctx: dict = {}
    if state:
        for key in ("anomaly", "safety", "weather", "idle", "idle_min", "fuel_pct"):
            if key in state:
                live_ctx[key] = state[key]
    merged_ctx = {**live_ctx, **shift_context}

    chunks = retrieve(question, top_k=3)
    sources = [
        {
            "id": i + 1,
            "title": c["title"],
            "section": c["section"],
            "excerpt": c["content"][:200] + ("..." if len(c["content"]) > 200 else ""),
            "knowledge_id": c["id"],
        }
        for i, c in enumerate(chunks)
    ]

    # Try LLM first
    if ai.llm_available() and chunks:
        try:
            prompt = _build_prompt(question, chunks, merged_ctx)
            resp = ai._client.messages.create(
                model=ai.LLM_MODEL,
                max_tokens=1500,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            if resp.stop_reason != "refusal":
                text = " ".join(b.text for b in resp.content if b.type == "text").strip()
                if text:
                    return {
                        "answer": text,
                        "sources": sources,
                        "source_type": "llm",
                        "grounded": True,
                        "model": ai.LLM_MODEL,
                    }
        except Exception as exc:
            pass  # Fall through to template

    # Template fallback
    template_text = _template_answer(question, chunks, merged_ctx)
    return {
        "answer": template_text,
        "sources": sources,
        "source_type": "template",
        "grounded": bool(chunks),
        "note": "LLM unavailable — answer generated from retrieved documentation only.",
    }
