from pydantic import BaseModel, Field
from enum import Enum

class QuestionType(str, Enum):
    CHOICE = "choice"; JUDGMENT = "judgment"; FILL_BLANK = "fill_blank"; SHORT_ANSWER = "short_answer"; ESSAY = "essay"

class Difficulty(str, Enum):
    EASY = "easy"; MEDIUM = "medium"; HARD = "hard"

class ChoiceQuestion(BaseModel):
    type: QuestionType = QuestionType.CHOICE
    stem: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)
    difficulty: Difficulty = Difficulty.MEDIUM
    knowledge_point: str = ""
    explanation: str = ""

class JudgmentQuestion(BaseModel):
    type: QuestionType = QuestionType.JUDGMENT
    stem: str; judgment: bool
    difficulty: Difficulty = Difficulty.MEDIUM; knowledge_point: str = ""; explanation: str = ""

class FillBlankQuestion(BaseModel):
    type: QuestionType = QuestionType.FILL_BLANK
    stem: str; answers: list[str]
    difficulty: Difficulty = Difficulty.MEDIUM; knowledge_point: str = ""; explanation: str = ""

class ShortAnswerQuestion(BaseModel):
    type: QuestionType = QuestionType.SHORT_ANSWER
    stem: str; reference_answer: str = ""; scoring_criteria: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.MEDIUM; knowledge_point: str = ""; explanation: str = ""

class EssayQuestion(BaseModel):
    type: QuestionType = QuestionType.ESSAY
    stem: str; reference_answer: str; scoring_criteria: list[str]
    difficulty: Difficulty = Difficulty.MEDIUM; knowledge_point: str = ""; explanation: str = ""
