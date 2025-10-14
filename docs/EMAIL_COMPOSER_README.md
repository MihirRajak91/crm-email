# Email Composition Pipeline

This document explains how CRM composes status-aware emails, from the HTTP request that reaches FastAPI to the final response returned to the client. Use it as a reference when modifying retrieval logic, swapping LLM providers, or debugging production issues.

## High-Level Flow

1. **Client request** hits `POST /api/email/compose` with a `ComposeEmailRequest` payload.
2. **FastAPI router** validates the payload and forwards it to `EmailComposerService.compose`.
3. **Retrieval step** builds a synthetic search query from status, email thread text, and recipient hints, embeds it, and performs a Qdrant similarity search.
4. **Context digest** condenses retrieved chunks into a short bullet list that becomes a dedicated message for the LLM.
5. **Prompt selection** chooses one of four templates (`new`, `contacted`, `qualified`, `lost`) and formats a JSON-oriented completion request.
6. **LLM invocation** runs through the configured provider (OpenAI or fallback) and returns raw text.
7. **Post-processing** parses JSON content, trims whitespace, and structures a `ComposeEmailResponse`.
8. **Response formatter** wraps the output with the standard API envelope and returns a 200 JSON response.

## Key Components

| Responsibility | File / Class |
| --- | --- |
| API route & logging | `crm/routers/email_router.py` |
| Request/response schema | `crm/models/email_models.py` |
| Service orchestration | `crm/services/email_composer_service.py` |
| Prompts & templates | `crm/prompts/email_prompts.py` |
| Embedding helper | `crm/utils/embedder.py` |
| Qdrant client bootstrap | `crm/utils/qdrand_db.py` |
| Settings & env management | `crm/core/settings.py` |
| LLM provider selection | `crm/services/llm_service.py` |
| Standard responses | `crm/utils/response_formatter.py` |

## Request Payload

`ComposeEmailRequest` fields (`crm/models/email_models.py`):

- `status`: required `StatusEnum` (`new`, `contacted`, `qualified`, `lost`).
- `past_emails`: list of `EmailThreadMessage` objects with optional `subject` and required `body`.
- `recipient_name`, `recipient_company`: optional personalization hints.
- `top_k`: number of vector hits to retrieve (default 6, clamped to 1–20).

### Sample Request

```json
{
  "status": "contacted",
  "past_emails": [
    {"subject": "Quick intro", "body": "Hi Sam, wanted to introduce..."},
    {"body": "Thanks for reaching out, can you share integration details?"}
  ],
  "recipient_name": "Sam",
  "recipient_company": "Globex",
  "top_k": 6
}
```

## Router Responsibilities

`crm/routers/email_router.py`

- Logs a sanitized preview of the email thread to avoid dumping full bodies into logs.
- Instantiates a singleton `EmailComposerService` and calls `compose`.
- Wraps success with `format_success_response` and errors with `format_error_response`.

## EmailComposerService Internals

`crm/services/email_composer_service.py`

### Initialization

- Pulls shared singletons for LLM (`llm_service.llm`), embeddings (`utils.embedder.embedder`), and Qdrant (`utils.qdrand_db.client`).
- Loads application settings via `get_settings()` and caches `COLLECTION_NAME` for searches.

### Retrieval Workflow

1. **Query seeds**
   - Adds status-specific hints (e.g., "overview, value proposition" when status is `new`).
   - Appends concatenated thread text (first and last message extracted in `_thread_segments`).
   - Includes `recipient_company` / `recipient_name` if supplied.
2. **Embedding**
   - Joins seeds into one string (fallback "product overview value proposition features case studies" if empty).
   - Calls `_embed_query` which runs the async embedder; default is OpenAI `text-embedding-3-small` in non-dev environments.
3. **Qdrant search**
   - Executes `client.search(...)` with the query vector, `top_k` limit, and no additional filters.
   - Collects `payload["text"]` for context and constructs `SourceRef` objects with `resource_id`, `chunk_id`, `title`.

> **Note:** Retrieval gracefully degrades to empty context if Qdrant raises, ensuring the API still returns a response.

### Context Digest

- If context text is non-empty, formats `CONTEXT_DIGEST_TEMPLATE` and invokes the LLM to transform the raw chunks into ≤6 bullet points.
- Digest is used as a separate prompt field to keep downstream templates compact and grounded.

### Status-Specific Composition

Each status calls its corresponding template with the digest and relevant thread excerpts:

- `_compose_new`: cold outreach, uses digest only.
- `_compose_contacted`: includes first and latest thread bodies (trimmed) to react to replies.
- `_compose_qualified`: similar to contacted but longer copy and explicit next steps.
- `_compose_lost`: graceful close referencing the latest email.

All templates enforce JSON output with `subject` and `body`. `_invoke_text` handles differences between LangChain `LLMResult` objects and raw strings.

### Post-Processing

- `_parse_json` attempts direct `json.loads` and falls back to locating the first `{...}` block to tolerate minor formatting drift.
- `ComposeEmailResponse` ensures trimmed `subject` / `body` strings.

## Prompt Templates

`crm/prompts/email_prompts.py`

- Built with `langchain.prompts.PromptTemplate`.
- `CONTEXT_DIGEST_TEMPLATE`: instructs the model to produce factual bullets.
- `EMAIL_*_TEMPLATE` variations embed guardrails on tone, length, CTA expectations, and output format.
- All generation prompts demand "Return ONLY minified JSON" to simplify parsing.

## LLM & Embedding Providers

- `crm/services/llm_service.py` reads `LLM_PROVIDER` from settings (`openai | ollama | fallback`).
- If OpenAI credentials fail, automatically falls back to Ollama and finally to a static fallback response.
- `crm/utils/embedder.py` mirrors this approach: defaults to OpenAI embeddings when `ENV != dev`, otherwise uses local model configs (`LOCAL_EMBEDDING_MODEL`).

Environment variables are managed by `crm/core/settings.py`. Key values for composing emails:

- `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_LLM_MODEL`
- `EMBEDDING_MODEL`, `USE_OPENAI`, `OPENAI_EMBEDDING_MODEL`
- `QDRANT_HOST`, `QDRANT_PORT`, `COLLECTION_NAME`

## Running the Endpoint Locally

1. Ensure supporting services are reachable (MongoDB, Qdrant, optional Redis/RabbitMQ).
2. Start the API:
   ```bash
   poetry install  # once
   poetry run uvicorn crm.main:app --host 0.0.0.0 --port 8001 --reload
   ```
3. Issue the request:
   ```bash
   curl -X POST http://localhost:8001/api/email/compose \
     -H 'Content-Type: application/json' \
     -d '{"status":"new","past_emails":[],"recipient_name":"Alex","recipient_company":"Acme Corp"}'
   ```
4. Expect a response shaped like:
   ```json
   {
     "status": "success",
     "message": "Email composed successfully",
     "data": {
       "subject": "...",
       "body": "..."
     }
   }
   ```

## Observability & Logging

- Router logs thread count plus a truncated preview of the first email.
- Retrieval logs the length of aggregated context and number of source chunks (`EmailComposerService.compose`).
- Failures in Qdrant, Redis, RabbitMQ, or LLM initialization emit errors but usually allow requests to continue with degraded functionality.

## Error Handling & Resilience

- Missing/invalid payload fields are caught by Pydantic before hitting business logic.
- Qdrant failures return empty context, leading the LLM to compose using only system prompts and minimal personalization.
- `_parse_json` prevents hard failures on slight prompt drift by returning empty strings.
- Route-level exception handler converts any uncaught error into a 500 response with `format_error_response`.

## Extending the Pipeline

- **New statuses**: add enum value, extend `_retrieve` hinting, create a new prompt template, and wire it into the status switch.
- **Metadata filters**: update `_retrieve` to pass `query_filter` to Qdrant when tagging documents.
- **LLM provider swap**: implement the provider in `services/llm_service.py` and ensure it exposes `.invoke`.
- **Response shape changes**: modify `ComposeEmailResponse` and adjust prompt JSON keys accordingly.

## Testing & Validation Tips

- Unit-test `_thread_segments`, `_parse_json`, and retrieval query generation with synthetic payloads.
- Mock `self.llm.invoke` to verify prompt formatting and ensure JSON is preserved.
- For integration testing, spin up Qdrant via Docker and seed a handful of documents; assert that compose returns grounded references.
- Monitor latency: embedding + LLM calls dominate; consider using async gather if batching becomes necessary.

## Troubleshooting Checklist

| Symptom | Likely Cause | Suggested Fix |
| --- | --- | --- |
| Startup fails with Qdrant connection error | Qdrant host/port unreachable or collection init failing | Confirm access, set `QDRANT_SKIP_COLLECTION_INIT`, or clean storage directory |
| API returns fallback text | `LLM_PROVIDER` misconfigured or provider down | Verify env vars, check provider logs, ensure API keys |
| Emails lack context | Retrieval returned no hits | Inspect Qdrant data, increase `top_k`, refine query seeding |
| JSON parsing errors | LLM ignored instructions | Tighten prompt instructions or post-process with `json.loads` + regex cleanup |

## Related Resources

- [`docs/DEVELOPER_ONBOARDING.md`](DEVELOPER_ONBOARDING.md) – project-wide architecture
- [`docs/CONTENT_BASED_CHUNKING_README.md`](CONTENT_BASED_CHUNKING_README.md) – ingestion pipeline
- [`docs/TABLE_AWARE_CHUNKING_README.md`](TABLE_AWARE_CHUNKING_README.md) – splitter background

