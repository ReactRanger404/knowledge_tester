"""本 Agent 所用模型 — 完全自包含。"""
from pydantic import BaseModel, Field

class KnowledgePoint(BaseModel):
    concept: str = Field(description="知识点核心概念名")
    importance: float = Field(ge=0, le=1)
    keywords: list[str] = Field(default_factory=list)

class KnowledgeExtractionResult(BaseModel):
    knowledge_points: list[KnowledgePoint]
    summary: str = ""
