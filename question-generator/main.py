"""Agent ② 出题 — 基于上下文出通用题（RawQuestion）。"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi import FastAPI
from llm import chat_structured
from models import RawQuestion

SYSTEM = """你是大学专业课出题教师。根据知识点和教材原文出一道选择题。
要求：
- 题目有区分度，考核心概念而非细枝末节
- 题干清晰不含糊，读完就知道问什么
- **题目必须自包含，不能引用图表、图片、公式截图、上下文中的例子等学生看不到的内容**
- 干扰项必须是真实存在的常见错误理解（不是随手编的）
- 如果给了"上下文"，必须基于上下文出题，不能编造
- **explanation 必填**，写清楚为什么正确答案是对的、其他选项错在哪，不少于 20 字

输出 JSON：
{"stem": "题干", "correct_answer": "正确答案", "distractors": ["典型错误1","典型错误2","典型错误3"], "knowledge_point": "知识点名", "difficulty": "medium", "explanation": "解析"}"""

app = FastAPI(title="Question Generator")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload", {}); msg_type = body.get("type", "")

    if msg_type == "revise_question":
        user = f"以下是之前出的题，审核未通过：\n原题：{p.get('original_question',{}).get('stem','')}\n反馈：\n" + "\n".join(f"- {s}" for s in p.get("suggestions",[])) + "\n\n请修改。"
        try:
            result = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":user}], RawQuestion)
        except Exception as e:
            return {"type": "question_revised", "payload": {"raw_question": {}}, "error": str(e)}
        if result is None:
            return {"type": "question_revised", "payload": {"raw_question": {}}, "error": "LLM returned empty"}
        return {"type": "question_revised", "payload": {"raw_question": result.model_dump()}, "error": None}

    kp = p.get("knowledge_point", "")
    ctx = p.get("context", "")
    imp = p.get("importance", 0.5)
    diff = p.get("difficulty", "medium")
    user = f"知识点：{kp}\n上下文：{ctx}\n重要度：{imp}\n目标难度：{diff}"

    try:
        result = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":user}], RawQuestion)
    except Exception as e:
        return {"type": "question_generated", "payload": {"raw_question": {}}, "error": str(e)}
    if result is None:
        return {"type": "question_generated", "payload": {"raw_question": {}}, "error": "LLM returned empty"}
    return {"type": "question_generated", "payload": {"raw_question": result.model_dump()}, "error": None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"question-generator"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8002)
