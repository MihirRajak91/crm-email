# utils/conversation_logger.py
import json
import asyncio
import threading
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any
from nltk.translate.bleu_score import sentence_bleu
import nltk
from crm.utils.logger import logger
import tiktoken

# Ensure NLTK punkt tokenizer is present
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOG_DIR = os.path.join(project_root, 'conversation_logs')
os.makedirs(LOG_DIR, exist_ok=True)

RAW_LOG_FILE= os.path.join(LOG_DIR, f"conversations_{datetime.utcnow():%Y_%m_%d}.log")
ENRICHED_FILE= os.path.join(LOG_DIR, f"conversations_enriched_{datetime.utcnow():%Y_%m_%d}.log")
LLM_MODEL= "llama3.1:latest"

# ------------------------------------------------------------------
# Public async entry-point
# ------------------------------------------------------------------
async def log_conversation_event(
    user_id: str,
    org_id: str,
    conversation_id: str,
    user_query: str,
    qdrant_search_result: List[Any],
    conversation_history: str,
    prompt: str,
    response: str,
    llm_model: str = LLM_MODEL,
    groundedness_score: float = None,
    related_to_previous: bool = False
) -> Dict[str, Any]:
    """
    Writes the raw event and then spawns a background thread
    that enriches it with BLEU, hallucination score & latency.
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "org_id": org_id,
        "conversation_id": conversation_id,
        "user_query": user_query,
        "qdrant_search_result": qdrant_search_result,
        "conversation_history": conversation_history,
        "prompt": prompt,
        "response": response,
        "llm_model": llm_model,
        "groundedness_score": groundedness_score,
        "related_to_previous": related_to_previous,
        "event_id": str(uuid.uuid4()),
        "latency_breakdown": None,  # filled in background
        "bleu_score": None,
        "hallucination_score": None
    }

    # Token count
    input_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    output_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    input_tokens = input_encoding.encode(prompt)
    output_tokens = output_encoding.encode(response)
    event["token_count"] = {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens
    }
    logger.info(f"Logging conversation event: {event['event_id']} for user {user_id} in org {org_id}")

    # 1. Raw log (fail silently)
    try:
        with open(RAW_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # 2. Fire-and-forget enrichment
    threading.Thread(
        target=_enrich_and_append,
        args=(event.copy(),),
        daemon=True
    ).start()

    return event

# ------------------------------------------------------------------
# Background enrichment
# ------------------------------------------------------------------
def _enrich_and_append(event: Dict[str, Any]) -> None:
    """
    Runs in a daemon thread. Adds:
      - BLEU (reference = source docs, candidate = LLM response)
      - Hallucination score (via LLM self-critique)
      - Latency breakdown (dummy numbers, replace with real ones)
    """
    try:
        # Build reference corpus
        docs = [chunk["text"] for chunk in event["qdrant_search_result"] if chunk.get("text")]
        reference = " ".join(docs).split()
        candidate = event["response"].split()

        # BLEU
        bleu = sentence_bleu([reference], candidate) if reference else 0.0

        # Hallucination via LLM self-critique
        hallucination = asyncio.run(_hallucination_score_via_llm(
            event["response"], docs
        ))

        # Latency placeholder (replace with real metrics if available)
        latency = {
            "embedding_ms": 120,
            "search_ms": 85,
            "llm_ms": 2100,
            "total_ms": 2305
        }

        # Enrich
        event.update({
            "bleu_score": round(bleu, 4),
            "hallucination_score": round(hallucination, 4),
            "latency_breakdown": latency
        })

        # Append silently
        with open(ENRICHED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    except Exception:
        pass  # Silent failure

# ------------------------------------------------------------------
# LLM-based hallucination check
# ------------------------------------------------------------------
async def _hallucination_score_via_llm(response: str, sources: List[str]) -> float:
    """
    Returns 0.0 (perfect) → 1.0 (complete hallucination).
    Uses a short prompt that asks the model to self-critique.
    """
    try:
        from crm.services.ollama_services import llm  # reuse your existing LLM

        source_text = "\n".join(sources)[:3000]  # truncate for speed
        prompt = f"""
            You are an evaluator. Given the assistant's final answer and the source documents, output only a number between 0 and 1 indicating how much of the answer is **not supported** by the sources (hallucination). 0 = fully supported, 1 = completely hallucinated.

            === Sources ===
            {source_text}

            === Assistant Answer ===
            {response}

            Hallucination score (0-1):
        """
        raw = llm.invoke(prompt).strip()
        logger.debug(f"[Hallucination Score] Raw response: {raw}")
        score = float(raw.split()[0])
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.5  # neutral fallback

