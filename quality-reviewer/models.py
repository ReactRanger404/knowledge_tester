from pydantic import BaseModel, Field
from enum import Enum

class Verdict(str, Enum):
    PASS = "pass"; REVISE = "revise"; REJECT = "reject"

class ReviewDimension(BaseModel):
    correctness: float = Field(ge=0,le=1)
    unambiguity: float = Field(ge=0,le=1)
    relevance: float = Field(ge=0,le=1)
    difficulty_match: float = Field(ge=0,le=1)

class ReviewResult(BaseModel):
    verdict: Verdict
    dimensions: ReviewDimension
    suggestions: list[str] = Field(default_factory=list)
