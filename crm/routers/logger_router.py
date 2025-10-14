from fastapi import APIRouter, Body
from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from collections import deque
import json
from crm.utils.logger import logger

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
logger.info(f"Project root directory: {PROJECT_ROOT}")
CONVERSATIONAL_LOG_DIR = PROJECT_ROOT / "conversation_logs"

class LogFilterForm(BaseModel):
    """
    Pydantic-compatible plain dataclass for the JSON body
    """
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    day: Optional[date] = None
    enriched: bool = False
    offset: int = 0
    limit: int = 100
    order: str = Field("asc", description="Order of logs: 'asc' for ascending, 'desc' for descending")

@router.post("/logs/conversations", response_model=List[Dict[str, Any]])
async def get_conversational_logs(
    form: LogFilterForm = Body(...)
) -> List[Dict[str, Any]]:
    """
    Accept a JSON form body for date filters and pagination.
    """
    logger.info("Payload received : ", form.model_dump() )
    # choose file
    stem = f"conversations_{date.today():%Y_%m_%d}.log"
    if form.enriched:
        stem = f"conversations_enriched_{date.today():%Y_%m_%d}.log"
    if form.day:
        stem = f"conversations_{form.day:%Y_%m_%d}.log"
        if form.enriched:
            stem = f"conversations_enriched_{form.day:%Y_%m_%d}.log"

    file_path = CONVERSATIONAL_LOG_DIR / stem
    logger.info(f"Reading logs from: {file_path}")
    if not file_path.exists():
        return []

    lines = []
    with file_path.open("rt", encoding="utf-8") as f:
        if form.order == "asc":
            # Read the file in normal order
            buffer = f.readlines()
        else:
            # Read the file in reverse order using deque
            f.seek(0, 2)  # Move to the end of the file
            size = f.tell()
            f.seek(0, 0)  # Move back to the start
            buffer = deque()
            while f.tell() < size:
                line = f.readline()
                buffer.appendleft(line)

        for ln in buffer:
            try:
                rec = json.loads(ln)
                ts = date.fromisoformat(rec["timestamp"][:10])
                if form.from_date and ts < form.from_date:
                    continue
                if form.to_date and ts > form.to_date:
                    continue
                lines.append(rec)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    # Apply pagination
    return lines[form.offset : form.offset + form.limit]