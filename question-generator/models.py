from pydantic import BaseModel, Field
from enum import Enum

class Difficulty(str, Enum):
    EASY = "easy"; MEDIUM = "medium"; HARD = "hard"

class RawQuestion(BaseModel):
    stem: str
    difficulty: Difficulty = Difficulty.MEDIUM
    knowledge_point: str = ""
    correct_answer: str = ""
    distractors: list[str] = Field(default_factory=list)
    explanation: str = ""
