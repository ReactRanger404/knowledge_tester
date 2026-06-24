"""Agent ③ 题型适配。"""
from fastapi import FastAPI
from llm import chat_structured
from models import ChoiceQuestion, JudgmentQuestion, FillBlankQuestion, ShortAnswerQuestion, EssayQuestion

TYPE_MAP = {"choice": ChoiceQuestion, "judgment": JudgmentQuestion, "fill_blank": FillBlankQuestion, "short_answer": ShortAnswerQuestion, "essay": EssayQuestion}
SYSTEM = "将原始题目转为指定题型。保持知识点和难度不变。\n\n选择题返回 JSON：{\"type\":\"choice\",\"stem\":\"题干\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"correct_index\":0,\"difficulty\":\"medium\",\"knowledge_point\":\"\",\"explanation\":\"\"}\n判断题返回 JSON：{\"type\":\"judgment\",\"stem\":\"题干\",\"judgment\":true,\"difficulty\":\"medium\",\"knowledge_point\":\"\",\"explanation\":\"\"}"

app = FastAPI(title="Type Adapter")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); raw = p.get("raw_question",{}); t = p.get("target_type","choice")
    m = TYPE_MAP.get(t)
    if not m: return {"type":"error","payload":{},"error":f"unsupported: {t}"}
    try:
        result = await chat_structured([
            {"role":"system","content":SYSTEM},
            {"role":"user","content":f"转为「{t}」题型：\n题干：{raw.get('stem','')}\n答案：{raw.get('correct_answer','')}\n干扰项：{', '.join(raw.get('distractors',[]))}\n知识点：{raw.get('knowledge_point','')}\n难度：{raw.get('difficulty','medium')}"}
        ], m)
    except Exception as e:
        return {"type":"type_adapted","payload":{"formatted_question":{}},"error":str(e)}
    if result is None:
        return {"type":"type_adapted","payload":{"formatted_question":{}},"error":"LLM returned empty content"}
    return {"type":"type_adapted","payload":{"formatted_question":result.model_dump(),"knowledge_point":raw.get("knowledge_point","")},"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"type-adapter"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8003)
