"""判断题 tool 定义。"""

TOOL_JUDGMENT = {
    "type": "function",
    "function": {
        "name": "create_judgment_question",
        "description": "创建一道判断题",
        "parameters": {
            "type": "object",
            "properties": {
                "stem": {"type": "string"},
                "judgment": {"type": "boolean"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "knowledge_point": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["stem", "judgment", "difficulty", "explanation"],
        },
    },
}
