import re
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import groq as groq_sdk
from google import genai
from google.genai.types import GenerateContentConfig
from google.genai import errors as genai_errors
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.core.markers import Marker

_gemini_client: Optional[genai.Client] = None
_groq_client: Optional[groq_sdk.AsyncGroq] = None


@dataclass
class AnswerResult:
    text: str
    # True only for rule-based summaries. LLM answers are False and get cached;
    # rule-based summaries are not cached so a later retry can produce a real answer.
    is_fallback: bool


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _get_groq_client() -> groq_sdk.AsyncGroq:
    global _groq_client
    if _groq_client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        _groq_client = groq_sdk.AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client


def _rule_based_summary(
    text: str, noise_filters: list[str], max_sentences: int = 5
) -> str:
    """
    Fallback when all LLM providers are unavailable.
    Strips noise patterns and phone numbers, returns first clean sentences.
    """
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)

    filtered: list[str] = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        lower = s.lower()
        if any(f in lower for f in noise_filters):
            continue
        if re.search(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b", s):
            continue
        filtered.append(s)
        if len(filtered) >= max_sentences:
            break

    if not filtered:
        filtered = [s.strip() for s in sentences[:max_sentences] if s.strip()]

    return " ".join(filtered)


def _build_fallback(rag_context: str, noise_filters: list[str]) -> AnswerResult:
    summary = _rule_based_summary(rag_context, noise_filters)
    if not summary:
        return AnswerResult(
            text=(
                "Unable to generate an answer from the available information. "
                "There may not be enough reliable context to respond without speculation."
            ),
            is_fallback=True,
        )
    return AnswerResult(
        text=(
            "Concise summary couldn't be generated. Here is extracted context:\n\n"
            f"{summary}\n\n"
            "This information is general and does not replace advice from a qualified professional."
        ),
        is_fallback=True,
    )


def _build_prompt(rag_context: str, user_query: str) -> str:
    return "\n".join([
        "RAG CONTEXT (verbatim):",
        rag_context.strip(),
        "\nUSER QUESTION:",
        user_query.strip(),
    ])


# Retry on 503 / transient server errors. ClientError (4xx) is not retried
# since those indicate bad requests or auth failures, not transient outages.
@retry(
    retry=retry_if_exception_type(genai_errors.ServerError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def _call_gemini(prompt: str, system_instruction: str) -> str:
    response = await _get_gemini_client().aio.models.generate_content(
        model=settings.gemini_flash_model,
        contents=prompt,
        config=GenerateContentConfig(system_instruction=[system_instruction]),
    )
    return (response.text or "").strip()


# Retry on 5xx and rate-limit errors; Groq free tier can hit 429s under load.
@retry(
    retry=retry_if_exception_type((groq_sdk.InternalServerError, groq_sdk.RateLimitError)),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(2),
    reraise=True,
)
async def _call_groq(prompt: str, system_instruction: str) -> str:
    response = await _get_groq_client().chat.completions.create(
        model=settings.groq_fallback_model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def generate_answer(
    rag_context: str,
    user_query: str,
    system_prompt: str,
    noise_filters: list[str],
) -> AnswerResult:
    """
    Tries Gemini (3 attempts) → Groq (2 attempts) → rule-based fallback.
    Only LLM-generated answers are marked is_fallback=False (eligible for caching).
    """
    if not rag_context or not rag_context.strip():
        return AnswerResult(
            text="No relevant context was found in the knowledge base to answer this question.",
            is_fallback=False,
        )

    prompt = _build_prompt(rag_context, user_query)

    try:
        text = await _call_gemini(prompt, system_prompt)
        if text:
            return AnswerResult(text=text, is_fallback=False)
    except Exception as e:
        print(f"  {Marker.CROSS} Gemini unavailable ({type(e).__name__}) — trying Groq...")

    try:
        text = await _call_groq(prompt, system_prompt)
        if text:
            return AnswerResult(text=text, is_fallback=False)
    except Exception as e:
        print(f"  {Marker.CROSS} Groq unavailable ({type(e).__name__}) — using rule-based summary")

    return _build_fallback(rag_context, noise_filters)


async def stream_answer(
    rag_context: str,
    user_query: str,
    system_prompt: str,
    noise_filters: list[str],
) -> AsyncIterator[str]:
    """
    Yields text chunks as they arrive from the LLM for SSE delivery.
    No retries — streaming is best-effort; callers should not cache the output.
    Falls back to yielding the full rule-based answer as a single chunk.
    """
    if not rag_context or not rag_context.strip():
        yield "No relevant context was found in the knowledge base to answer this question."
        return

    prompt = _build_prompt(rag_context, user_query)

    # Try Gemini streaming
    try:
        async for chunk in await _get_gemini_client().aio.models.generate_content_stream(
            model=settings.gemini_flash_model,
            contents=prompt,
            config=GenerateContentConfig(system_instruction=[system_prompt]),
        ):
            if chunk.text:
                yield chunk.text
        return
    except Exception as e:
        print(f"  {Marker.CROSS} Gemini stream unavailable ({type(e).__name__}) — trying Groq...")

    # Try Groq streaming
    try:
        stream = await _get_groq_client().chat.completions.create(
            model=settings.groq_fallback_model,
            max_tokens=1024,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
        return
    except Exception as e:
        print(f"  {Marker.CROSS} Groq stream unavailable ({type(e).__name__}) — using rule-based summary")

    # Rule-based fallback — yield as single chunk
    result = _build_fallback(rag_context, noise_filters)
    yield result.text
