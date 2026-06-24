"""论述题 tool 定义。"""

TOOL_ESSAY = {
    "type": "function",
    "function": {
        "name": "create_essay_question",
        "description": "创建一道论述题",
        "parameters": {
            "type": "object",
            "properties": {
                "stem": {"type": "string", "description": "题目题干"},
                "reference_answer": {"type": "string", "description": "参考答案要点"},
                "scoring_criteria": {"type": "array", "items": {"type": "string"}, "description": "评分标准列表"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "knowledge_point": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["stem", "reference_answer", "difficulty"],
        },
    },
}
