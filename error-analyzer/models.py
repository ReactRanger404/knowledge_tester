from pydantic import BaseModel, Field

class WeakConcept(BaseModel):
    concept: str; missed_count: int = Field(ge=1); total_count: int = Field(ge=1); mastery_ratio: float = Field(ge=0,le=1)

class ErrorPattern(BaseModel):
    pattern_name: str; description: str = ""; affected_question_indices: list[int] = Field(default_factory=list); frequency: int = 0

class ErrorAnalysisReport(BaseModel):
    exam_id: str = ""
    weak_concepts: list[WeakConcept] = Field(default_factory=list)
    error_patterns: list[ErrorPattern] = Field(default_factory=list)
    overall_mastery: float = Field(default=0.0,ge=0,le=1)
    summary: str = ""
    suggestion: str = ""
