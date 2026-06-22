"""Agent ④ 质量审核 — 含 revise 回路。"""
from fastapi import FastAPI
from llm import chat_structured
from models import ReviewResult, Verdict

SYSTEM = """严格审核题目质量。
维度：正确性、无歧义、相关性、难度匹配、干扰项质量。
输出 verdict: pass / revise / reject。不是 pass 必须给修改建议。"""

app = FastAPI(title="Quality Reviewer")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); q = p.get("formatted_question",p.get("raw_question",{})); rn = p.get("revision_round",0)
    result = await chat_structured([
        {"role":"system","content":SYSTEM},
        {"role":"user","content":f"知识点：{q.get('knowledge_point','')}\n题干：{q.get('stem','')}\n答案：{q.get('correct_answer','') or q.get('correct_index','') or q.get('judgment','')}\n干扰项：{q.get('distractors',[]) or q.get('options',[])}\n难度：{q.get('difficulty','medium')}"}
    ], ReviewResult)
    out = [{"type":"question_reviewed","payload":{"review":result.model_dump(),"question_data":q,"revision_round":rn},"error":None}]
    if result.verdict in (Verdict.REVISE, Verdict.REJECT) and rn < 3:
        out.append({"type":"revise_question","payload":{"original_question":q,"suggestions":result.suggestions,"revision_round":rn+1},"error":None})
    return out

@app.get("/health")
async def health():
    return {"status":"ok","name":"quality-reviewer"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8004)
