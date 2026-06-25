from pydantic import BaseModel, Field

class KnowledgeExplanation(BaseModel):
    question_index: int
    knowledge_point: str = ""
    explanation: str = ""

class ErrorAnalysisReport(BaseModel):
    exam_id: str = ""
    knowledge_explanations: list[KnowledgeExplanation] = Field(default_factory=list)
