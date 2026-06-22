from pydantic import BaseModel, Field

class GradingResult(BaseModel):
    question_index: int
    is_correct: bool
    score: float = Field(ge=0,le=100)
    max_score: float = Field(ge=0,le=100)
    feedback: str = ""
