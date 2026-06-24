"""Agent ② 出题 — 基于上下文出通用题（RawQuestion）。"""
from fastapi import FastAPI
from llm import chat_structured
from models import RawQuestion

SYSTEM = """你是一位专业的大学教师，根据教材原文出考题。
要求：
1. 题目必须有区分度，不能太简单
2. 干扰项必须是真实常见的错误理解，不能是随意编造
3. 如果给了上下文，必须基于上下文出题，不要自己编造内容
4. explanation 要写清楚为什么选这个答案
5. 每个知识点只出一道题

请严格返回以下 JSON 格式：
{"stem": "题目题干", "correct_answer": "正确答案", "distractors": ["干扰项1","干扰项2","干扰项3"], "knowledge_point": "知识点名", "difficulty": "easy/medium/hard", "explanation": "解析"}"""

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
