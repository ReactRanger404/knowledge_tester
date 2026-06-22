"""Agent ② 出题 — 支持 revise。"""
from fastapi import FastAPI
from llm import chat_structured
from models import RawQuestion

SYSTEM = """根据知识点生成题目。
题干清晰，答案唯一，干扰项是典型错误而非随机选项。"""

app = FastAPI(title="Question Generator")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload", {}); t = body.get("type", "")
    if t == "revise_question":
        user = f"以下是之前出的题，审核未通过：\n原题：{p.get('original_question',{}).get('stem','')}\n反馈：\n" + "\n".join(f"- {s}" for s in p.get("suggestions",[])) + "\n\n请修改。"
        out_type = "question_revised"
    else:
        user = f"知识点：{p.get('knowledge_point','')}\n上下文：{p.get('context','')}\n重要度：{p.get('importance',0.5)}\n目标难度：{p.get('difficulty','medium')}"
        out_type = "question_generated"
    result = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":user}], RawQuestion)
    return {"type": out_type, "payload": {"raw_question": result.model_dump()}, "error": None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"question-generator"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8002)
