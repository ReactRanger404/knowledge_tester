"""简答题 tool 定义。"""

TOOL_SHORT_ANSWER = {
    "type": "function",
    "function": {
        "name": "create_short_answer_question",
        "description": "创建一道简答题",
        "parameters": {
            "type": "object",
            "properties": {
                "stem": {"type": "string", "description": "题目题干"},
                "reference_answer": {"type": "string", "description": "参考答案"},
                "scoring_criteria": {"type": "array", "items": {"type": "string"}, "description": "得分点列表"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "knowledge_point": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["stem", "reference_answer", "difficulty"],
        },
    },
}
