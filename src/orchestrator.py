import os
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig
from google.genai import errors as genai_errors
import re

def _simple_filter_and_summarize(text: str, max_sentences: int = 5) -> str:
    """
    Lightweight, rule-based summarization as a fallback when the model
    cannot be called successfully.

    - Removes obvious noise like URLs, phone numbers, and postal addresses.
    - Returns the first few remaining sentences as a compact summary.
    """
    if not text:
        return ""

    # Collapse whitespace to make sentence splitting more robust.
    text = re.sub(r"\s+", " ", text).strip()

    # Naive sentence split.
    sentences = re.split(r"(?<=[.!?])\s+", text)

    filtered: list[str] = []
    for s in sentences:
        s_stripped = s.strip()
        if not s_stripped:
            continue

        lower = s_stripped.lower()

        # Filter out obvious non-clinical noise.
        if "http://" in lower or "https://" in lower or "www." in lower:
            continue
        if any(token in lower for token in [" avenue", " st.", " street", " pike", " room "]):
            continue
        if re.search(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b", s_stripped):
            continue

        filtered.append(s_stripped)
        if len(filtered) >= max_sentences:
            break

    if not filtered:
        filtered = [s.strip() for s in sentences[:max_sentences] if s.strip()]

    return " ".join(filtered)


def generate_filtered_answer(rag_context: str, user_query: str) -> str:
    """
    Public entrypoint for the orchestrator.

    Takes raw RAG output and the user query, and returns a single,
    human-readable, summarized answer. The system prompt (system_instruction)
    inside this module guides Gemini to:
    - Focus on clinically relevant information from the context.
    - Filter out noisy details like phone numbers, URLs, author names,
      and publication metadata.
    - Answer concisely and avoid speculation.
    """
    return generate_orchestrator_system_prompt(rag_context, user_query=user_query)


load_dotenv()


_GEMINI_MODEL_NAME = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """
    Lazily create and cache a Google GenAI client using GEMINI_API_KEY.
    """
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Please add it to your environment or .env file."
        )

    _client = genai.Client(api_key=api_key)
    return _client


def generate_orchestrator_system_prompt(rag_context: str, user_query: Optional[str] = None) -> str:
    """
    Use Gemini Flash to turn raw RAG context into a concise, human-readable
    system prompt that can be passed to a downstream QA model.

    - Filters noisy / low-signal fragments.
    - Summarizes key facts and constraints.
    - Instructs the QA model to stay grounded in this context.
    """
    if not rag_context or not rag_context.strip():
        return (
            "You are a medical question-answering assistant. There is currently no "
            "relevant retrieved context available, so you must politely state that "
            "you cannot answer based on the provided data."
        )

    client = _get_client()

    system_instruction = (
        "You are a medical RAG orchestrator that generates FINAL ANSWERS for the "
        "user, not additional prompts.\n\n"
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
        "5) Does NOT mention RAG, retrieval, context chunks, or that you are an "
        "   orchestrator; it should read like a normal assistant answer.\n"
        "6) Is concise: prefer short paragraphs and avoid long lists of near-"
        "   duplicate details.\n\n"
        "Output requirements:\n"
        "- Output ONLY the final answer text, with no markdown headings, labels, or "
        "  JSON.\n"
        "- Do not invent new medical facts that are not implied by the context.\n"
        "- You may include a brief safety note that this is not a substitute for "
        "  professional medical advice.\n"
    )

    user_parts = [
        "RAG CONTEXT (verbatim):",
        rag_context.strip(),
    ]

    if user_query and user_query.strip():
        user_parts.append("\nUSER QUESTION:")
        user_parts.append(user_query.strip())

    prompt = "\n".join(user_parts)

    try:
        response = client.models.generate_content(
            model=_GEMINI_MODEL_NAME,
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=[system_instruction],
            ),
        )
    except genai_errors.ClientError:
        # If the model call fails entirely, fall back to a simple,
        # rule-based summary of the RAG context.
        summary = _simple_filter_and_summarize(rag_context)
        if not summary:
            return (
                "I'm unable to generate an answer from the available information. "
                "There may not be enough reliable context to respond without "
                "speculation."
            )
        return (
            "Here is a concise summary based on the available medical context:\n\n"
            f"{summary}\n\n"
            "This information is general and does not replace advice from a qualified "
            "healthcare professional."
        )

    text = (response.text or "").strip()

    if not text:
        summary = _simple_filter_and_summarize(rag_context)
        if not summary:
            return (
                "I'm unable to generate an answer from the available information. "
                "There may not be enough reliable context to respond without "
                "speculation."
            )
        return (
            "Here is a concise summary based on the available medical context:\n\n"
            f"{summary}\n\n"
            "This information is general and does not replace advice from a qualified "
            "healthcare professional."
        )

    return text

