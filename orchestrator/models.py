"""Orchestrator 自用模型 — 用于反序列化 Agent 响应。"""
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Union

class Difficulty(str, Enum):
    EASY="easy"; MEDIUM="medium"; HARD="hard"

class QuestionType(str, Enum):
    CHOICE="choice"; JUDGMENT="judgment"; FILL_BLANK="fill_blank"; SHORT_ANSWER="short_answer"; ESSAY="essay"

class ChoiceQuestion(BaseModel):
    type: QuestionType = QuestionType.CHOICE; stem: str; options: list[str]=Field(min_length=2,max_length=6)
    correct_index: int=Field(ge=0); difficulty: Difficulty=Difficulty.MEDIUM
    knowledge_point: str=""; explanation: str=""; bloom_level: str=""

class JudgmentQuestion(BaseModel):
    type: QuestionType = QuestionType.JUDGMENT; stem: str; judgment: bool
    difficulty: Difficulty=Difficulty.MEDIUM; knowledge_point: str=""; explanation: str=""

class FillBlankQuestion(BaseModel):
    type: QuestionType = QuestionType.FILL_BLANK; stem: str; answers: list[str]
    difficulty: Difficulty=Difficulty.MEDIUM; knowledge_point: str=""; explanation: str=""

class ShortAnswerQuestion(BaseModel):
    type: QuestionType = QuestionType.SHORT_ANSWER; stem: str; reference_answer: str=""
    scoring_criteria: list[str]=Field(default_factory=list); difficulty: Difficulty=Difficulty.MEDIUM
    knowledge_point: str=""; explanation: str=""

class EssayQuestion(BaseModel):
    type: QuestionType = QuestionType.ESSAY; stem: str; reference_answer: str; scoring_criteria: list[str]
    difficulty: Difficulty=Difficulty.MEDIUM; knowledge_point: str=""; explanation: str=""

FormattedQuestion = Union[ChoiceQuestion,JudgmentQuestion,FillBlankQuestion,ShortAnswerQuestion,EssayQuestion]

class ExamConfig(BaseModel):
    source_material: str = Field(default="", description="直接传入的文本内容")
    kb_name: str = Field(default="", description="从知识库加载的教材名（与 source_material 二选一）")
    question_types: list[str] = Field(default=["choice","judgment"])
    total_count: int = Field(default=10,ge=1,le=100)
    difficulty_distribution: dict[str,float] = Field(default_factory=lambda:{"easy":0.3,"medium":0.5,"hard":0.2})
    focus_knowledge: list[str] = Field(default_factory=list)

class ExamPaper(BaseModel):
    id: str; title: str=""; created_at: datetime=Field(default_factory=datetime.now)
    questions: list[FormattedQuestion]; question_count: int=Field(ge=1)
    difficulty_summary: dict[str,int]=Field(default_factory=dict)
    knowledge_coverage: list[str]=Field(default_factory=list)

class GradingResult(BaseModel):
    question_index: int; is_correct: bool; score: float=Field(ge=0,le=100); max_score: float=Field(ge=0,le=100); feedback: str=""

class GradingReport(BaseModel):
    exam_id: str; total_questions: int; correct_count: int; total_score: float; max_total_score: float
    results: list[GradingResult]; finished_at: datetime=Field(default_factory=datetime.now)

class WeakConcept(BaseModel):
    concept: str; missed_count: int=Field(ge=1); total_count: int=Field(ge=1); mastery_ratio: float=Field(ge=0,le=1)

class ErrorAnalysisReport(BaseModel):
    exam_id: str=""; weak_concepts: list[WeakConcept]=Field(default_factory=list)
    error_patterns: list=Field(default_factory=list); overall_mastery: float=Field(default=0.0,ge=0,le=1)
    summary: str=""; suggestion: str=""

class UserAnswer(BaseModel):
    exam_id: str; question_index: int; question_type: QuestionType; answer_text: str
