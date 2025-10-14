import json
import re
from crm.utils.logger import logger

def parse_response(response: str) -> dict:
    """
    Parse an LLM response that might be wrapped in ```json ... ``` fences.
    Returns a dict with keys:
        - "knowledge_request" : bool
        - "response"          : str
    Falls back gracefully if parsing fails.
    """
    try:
        # 1. Strip the optional ```json ... ``` wrapper
        stripped = re.sub(
            r'^```json\s*|\s*```$', '', response.strip(), flags=re.IGNORECASE
        ).strip()

        # 2. Parse JSON
        parsed = json.loads(stripped)

        # 3. Validate minimal structure
        if isinstance(parsed, dict):
            knowledge_request = bool(parsed.get("knowledge_request", False))
            response_text = str(parsed.get("response", ""))
            return {"knowledge_request": knowledge_request, "response": response_text}

        # Parsed JSON is not a dict → treat as plain text
        return {"knowledge_request": False, "response": str(parsed)}

    except Exception as e:
        logger.error(f"Failed to parse response as JSON: {response!r} -> {e}")
        return {"knowledge_request": False, "response": str(response)}