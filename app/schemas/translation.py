"""
Translation API schemas.
"""
from pydantic import BaseModel, Field


class TranslateTextRequest(BaseModel):
    """Translate arbitrary text to English."""

    text: str = Field(..., min_length=1, max_length=120_000)
