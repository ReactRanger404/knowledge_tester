"""填空题 tool 定义。"""

TOOL_FILL_BLANK = {
    "type": "function",
    "function": {
        "name": "create_fill_blank_question",
        "description": "创建一道填空题，题干中用____表示需要填写的内容",
        "parameters": {
            "type": "object",
            "properties": {
                "stem": {"type": "string", "description": "题干，用____表示填空位置"},
                "answers": {"type": "array", "items": {"type": "string"}, "description": "可接受的答案列表"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "knowledge_point": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["stem", "answers", "difficulty"],
        },
    },
}
