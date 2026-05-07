import os
import re
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
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
from _markers import Marker

load_dotenv()

_GEMINI_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
_GROQ_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")

_gemini_client: Optional[genai.Client] = None
_groq_client: Optional[groq_sdk.AsyncGroq] = None

_SYSTEM_INSTRUCTION = (
    "You are a medical assistant that generates FINAL ANSWERS for the user.\n\n"
    "You are given:\n"
    "- A block of raw retrieved context from a medical knowledge base.\n"
    "- The user's natural-language question.\n\n"
    "Your task is to produce a SINGLE concise, human-readable answer that:\n"
    "1) Summarizes only the clinically relevant information from the context in "
    "   clear everyday language.\n"
    "2) Filters out contact details, phone numbers, URLs, street addresses, "
    "   author/editor names, and publication metadata unless they are directly "
    "   necessary to answer the question.\n"
    "3) Focuses on definitions, mechanisms, indications, contraindications, "
    "   risks, benefits, and high-level treatment principles relevant to the "
    "   user's question.\n"
    "4) Explicitly avoids speculation and clearly states when the context does "
    "   not contain enough information to answer.\n"
    "5) Does NOT mention RAG, retrieval, or context chunks; it should read like "
    "   a normal assistant answer.\n"
    "6) Is concise: prefer short paragraphs and avoid near-duplicate details.\n\n"
    "Output ONLY the final answer text — no markdown headings, labels, or JSON.\n"
    "Do not invent medical facts not implied by the context.\n"
    "You may include a brief note that this is not a substitute for professional "
    "medical advice.\n"
)


@dataclass
class AnswerResult:
    text: str
    # True only for rule-based summaries. LLM answers (Gemini or Groq) are
    # False so they get cached; rule-based summaries are not cached since a
    # later retry may produce a better answer.
    is_fallback: bool


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Please add it to your environment or .env file."
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _get_groq_client() -> groq_sdk.AsyncGroq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Please add it to your environment or .env file."
            )
        _groq_client = groq_sdk.AsyncGroq(api_key=api_key)
    return _groq_client


def _rule_based_summary(text: str, max_sentences: int = 5) -> str:
    """
    Fallback used when all LLM providers are unavailable.
    Strips URLs, phone numbers, and address fragments, then returns the
    first `max_sentences` clean sentences from the context.
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
        if "http://" in lower or "https://" in lower or "www." in lower:
            continue
        if any(tok in lower for tok in [" avenue", " st.", " street", " pike", " room "]):
            continue
        if re.search(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b", s):
            continue
        filtered.append(s)
        if len(filtered) >= max_sentences:
            break

    if not filtered:
        filtered = [s.strip() for s in sentences[:max_sentences] if s.strip()]

    return " ".join(filtered)


def _build_fallback(rag_context: str) -> AnswerResult:
    summary = _rule_based_summary(rag_context)
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
            "This information is general and does not replace advice from a qualified "
            "healthcare professional."
        ),
        is_fallback=True,
    )


# Retry on 503 / transient server errors. ClientError (4xx) is not retried
# since those indicate bad requests or auth failures, not transient outages.
@retry(
    retry=retry_if_exception_type(genai_errors.ServerError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def _call_gemini(prompt: str) -> str:
    response = await _get_gemini_client().aio.models.generate_content(
        model=_GEMINI_MODEL,
        contents=prompt,
        config=GenerateContentConfig(system_instruction=[_SYSTEM_INSTRUCTION]),
    )
    return (response.text or "").strip()


# Retry on 5xx and rate-limit errors. Groq free tier can hit 429s under load.
@retry(
    retry=retry_if_exception_type((groq_sdk.InternalServerError, groq_sdk.RateLimitError)),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(2),
    reraise=True,
)
async def _call_groq(prompt: str) -> str:
    response = await _get_groq_client().chat.completions.create(
        model=_GROQ_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": _SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def generate_answer(rag_context: str, user_query: str) -> AnswerResult:
    """
    Synthesizes a clean, human-readable answer from raw RAG context.

    Tries Gemini first (3 attempts with exponential backoff on 503 errors),
    then falls back to Groq (2 attempts), then to a lightweight rule-based
    summary. Only LLM-generated answers are marked for caching; rule-based
    fallbacks are not, so a later retry can produce a better answer.
    """
    if not rag_context or not rag_context.strip():
        return AnswerResult(
            text="No relevant context was found in the knowledge base to answer this question.",
            is_fallback=False,
        )

    prompt = "\n".join([
        "RAG CONTEXT (verbatim):",
        rag_context.strip(),
        "\nUSER QUESTION:",
        user_query.strip(),
    ])

    try:
        text = await _call_gemini(prompt)
        if text:
            return AnswerResult(text=text, is_fallback=False)
    except Exception as e:
        print(f"  {Marker.CROSS} Gemini unavailable ({type(e).__name__}) — trying Groq...")

    try:
        text = await _call_groq(prompt)
        if text:
            return AnswerResult(text=text, is_fallback=False)
    except Exception as e:
        print(f"  {Marker.CROSS} Groq unavailable ({type(e).__name__}) — using rule-based summary")

    return _build_fallback(rag_context)
