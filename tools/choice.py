"""选择题 tool 定义。"""

TOOL_CHOICE = {
    "type": "function",
    "function": {
        "name": "create_choice_question",
        "description": "创建一道选择题",
        "parameters": {
            "type": "object",
            "properties": {
                "stem": {"type": "string", "description": "题目题干"},
                "options": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
                "correct_index": {"type": "integer", "description": "正确答案在 options 中的索引"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "knowledge_point": {"type": "string"},
                "explanation": {"type": "string", "description": "为什么选这个答案的解析"},
            },
            "required": ["stem", "options", "correct_index", "difficulty"],
        },
    },
}
