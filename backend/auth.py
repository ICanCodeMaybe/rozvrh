import logging
import os
import secrets

from fastapi import HTTPException, Request

ENV_VAR = "ROZVRH_API_KEY"

logger = logging.getLogger(__name__)


def get_api_key() -> str:
    key = os.environ.get(ENV_VAR)
    if key is None:
        key = secrets.token_urlsafe(32)
        os.environ[ENV_VAR] = key
        logger.warning("No %s set, generated a random key for this run: %s", ENV_VAR, key)
    return key


async def require_api_key(request: Request) -> None:
    expected = get_api_key()
    provided = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
