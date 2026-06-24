from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class Verdict(str, Enum):
    PASS = "pass"; REVISE = "revise"; REJECT = "reject"

class ReviewDimension(BaseModel):
    correctness: float = Field(ge=0,le=1)
    unambiguity: float = Field(ge=0,le=1)
    relevance: float = Field(ge=0,le=1)
    difficulty_match: float = Field(default=0.5, ge=0, le=1)

class ReviewResult(BaseModel):
    verdict: Verdict
    dimensions: ReviewDimension
    suggestions: list[str] = Field(default_factory=list)

class BatchReviewItem(BaseModel):
    index: int = Field(ge=0)
    verdict: str = "pass"
    justification: str = ""

class BatchReviewResponse(BaseModel):
    reviews: list[BatchReviewItem] = Field(default_factory=list)
