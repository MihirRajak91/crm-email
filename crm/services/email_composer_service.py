import json
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

# No direct chat role messages needed; prompts live in templates

from crm.services.llm_service import llm
from crm.utils.embedder import embedder
from crm.utils.qdrand_db import client
from crm.models.email_models import (
    ComposeEmailRequest,
    ComposeEmailResponse,
    StatusEnum,
    SourceRef,
)
from crm.prompts.email_prompts import (
    CONTEXT_DIGEST_TEMPLATE,
    EMAIL_NEW_TEMPLATE,
    EMAIL_CONTACTED_TEMPLATE,
    EMAIL_QUALIFIED_TEMPLATE,
    EMAIL_LOST_TEMPLATE,
)
from crm.utils.logger import logger
from crm.core.settings import get_settings


@dataclass
class RetrievalResult:
    context_text: str
    sources: List[SourceRef]


class EmailComposerService:
    """
    Compose status-aware emails with clear separation of system prompt, user query, and retrieved context.
    """

    def __init__(self):
        self.llm = llm
        self.embedder = embedder
        self.client = client
        self.settings = get_settings()
        self.collection_name = self.settings.COLLECTION_NAME

    # ------------------------- LLM helpers -------------------------
    # Prompts are defined in crm/prompts; invoke returns string content
    def _invoke_text(self, prompt: str) -> str:
        resp = self.llm.invoke(prompt)
        return resp.content if hasattr(resp, "content") else str(resp)

    # ------------------------- Retrieval -------------------------
    async def _embed_query(self, text: str) -> List[float]:
        vecs = await self.embedder.encode([text])
        return vecs[0]

    async def _retrieve(self, req: ComposeEmailRequest) -> RetrievalResult:
        """
        Retrieve relevant company/product docs from Qdrant without access filters.
        """
        # Build a retrieval query tuned by status and conversation context
        base = []

        if req.status == StatusEnum.NEW:
            base.append("overview, value proposition, benefits, features, proof points")
        elif req.status == StatusEnum.CONTACTED:
            base.append("address questions, objections, next steps, scheduling")
        elif req.status == StatusEnum.QUALIFIED:
            base.append("deployment, ROI, integration, pricing, next steps")
        elif req.status == StatusEnum.LOST:
            base.append("polite close, value reminder, reconnect later")

        past_email, latest_email, thread_body = self._thread_segments(req)
        if thread_body:
            base.append(thread_body[:600])

        if req.recipient_company:
            base.append(f"recipient company: {req.recipient_company}")
        if req.recipient_name:
            base.append(f"recipient name: {req.recipient_name}")

        query_text = ", ".join(base) or "product overview value proposition features case studies"
        query_vector = await self._embed_query(query_text)

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=req.top_k,
                query_filter=None,
            )
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            results = []

        texts: List[str] = []
        sources: List[SourceRef] = []
        for hit in results or []:
            payload = getattr(hit, "payload", {}) or {}
            text = payload.get("text")
            if text:
                texts.append(text)
            sources.append(
                SourceRef(
                    resource_id=payload.get("resource_id"),
                    chunk_id=str(payload.get("chunk_id")) if payload.get("chunk_id") else None,
                    title=payload.get("title") or payload.get("file_name"),
                )
            )

        context_text = "\n\n".join(texts)
        return RetrievalResult(context_text=context_text, sources=sources)

    # ------------------------- Digest -------------------------
    def _build_digest(self, context_text: str) -> str:
        """
        Create a concise digest of retrieved docs using the dedicated prompt template.
        """
        if not context_text:
            return ""
        prompt = CONTEXT_DIGEST_TEMPLATE.format(company_context=context_text)
        return self._invoke_text(prompt).strip()

    # ------------------------- Compose -------------------------
    def _compose_new(self, digest: str, req: ComposeEmailRequest) -> Dict[str, Any]:
        prompt = EMAIL_NEW_TEMPLATE.format(
            company_digest=digest,
            product_name="",
            company_name=self.settings.APP_NAME,
            recipient_name=req.recipient_name or "",
            recipient_company=req.recipient_company or "",
            persona="",
            industry="",
            language="",
        )
        raw = self._invoke_text(prompt)
        return self._parse_json(raw, keys=["subject", "body"])  # type: ignore

    def _compose_contacted(self, digest: str, req: ComposeEmailRequest) -> Dict[str, Any]:
        past_email_text, latest_email_text, _ = self._thread_segments(req)
        prompt = EMAIL_CONTACTED_TEMPLATE.format(
            company_digest=digest,
            past_email=past_email_text[:1500],
            latest_email=latest_email_text[:1500],
            product_name="",
            company_name=self.settings.APP_NAME,
            recipient_name=req.recipient_name or "",
            recipient_company=req.recipient_company or "",
            language="",
        )
        raw = self._invoke_text(prompt)
        return self._parse_json(raw, keys=["subject", "body"])  # type: ignore

    def _compose_qualified(self, digest: str, req: ComposeEmailRequest) -> Dict[str, Any]:
        past_email_text, latest_email_text, _ = self._thread_segments(req)
        prompt = EMAIL_QUALIFIED_TEMPLATE.format(
            company_digest=digest,
            past_email=past_email_text[:1200],
            latest_email=latest_email_text[:1200],
            product_name="",
            company_name=self.settings.APP_NAME,
            recipient_name=req.recipient_name or "",
            recipient_company=req.recipient_company or "",
            language="",
        )
        raw = self._invoke_text(prompt)
        return self._parse_json(raw, keys=["subject", "body"])  # type: ignore

    def _compose_lost(self, digest: str, req: ComposeEmailRequest) -> Dict[str, Any]:
        _, latest_email_text, _ = self._thread_segments(req)
        prompt = EMAIL_LOST_TEMPLATE.format(
            company_digest=digest,
            latest_email=latest_email_text[:800],
            product_name="",
            company_name=self.settings.APP_NAME,
            recipient_name=req.recipient_name or "",
            recipient_company=req.recipient_company or "",
            language="",
        )
        raw = self._invoke_text(prompt)
        return self._parse_json(raw, keys=["subject", "body"])  # type: ignore

    # ------------------------- Public API -------------------------
    async def compose(self, req: ComposeEmailRequest) -> ComposeEmailResponse:
        # Retrieve relevant docs
        retrieval = await self._retrieve(req)
        logger.info(
            f"Email compose retrieval: len_context={len(retrieval.context_text)}, sources={len(retrieval.sources)}"
        )
        # Build digest (separate context message)
        digest = self._build_digest(retrieval.context_text)

        # Compose according to status
        if req.status == StatusEnum.NEW:
            data = self._compose_new(digest, req)
        elif req.status == StatusEnum.CONTACTED:
            data = self._compose_contacted(digest, req)
        elif req.status == StatusEnum.QUALIFIED:
            data = self._compose_qualified(digest, req)
        else:
            data = self._compose_lost(digest, req)

        subject = str(data.get("subject", "")).strip()
        body = str(data.get("body", "")).strip()

        return ComposeEmailResponse(
            subject=subject,
            body=body,
        )

    # ------------------------- Utils -------------------------
    def _parse_json(self, text: str, keys: List[str]) -> Dict[str, Any]:
        try:
            data = json.loads(text)
            return {k: data.get(k) for k in keys}
        except Exception:
            # Attempt to extract JSON substring
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    data = json.loads(text[start : end + 1])
                    return {k: data.get(k) for k in keys}
            except Exception:
                pass
        # Fallback minimal
        return {k: "" for k in keys}

    def _thread_segments(self, req: ComposeEmailRequest) -> Tuple[str, str, str]:
        """Return (initial_outreach, latest_reply, combined_thread_text)."""

        bodies = [msg.body for msg in req.past_emails if msg.body]

        if not bodies:
            return "", "", ""

        past_email = bodies[0]
        latest_email = bodies[-1]
        combined = "\n\n".join(bodies)

        return past_email, latest_email, combined
