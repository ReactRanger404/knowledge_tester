"""Agent ⑦ 错题分析。"""
from fastapi import FastAPI
from llm import chat_structured
from models import ErrorAnalysisReport

SYSTEM = "分析错题，找出薄弱知识点和错误模式，给出学习建议。每个结论要在错题中有依据。"
app = FastAPI(title="Error Analyzer")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); errors = p.get("error_details",[]); total = p.get("total_count",0); eid = p.get("exam_id","")
    if not errors:
        return {"type":"errors_analyzed","payload":{"exam_id":eid,"weak_concepts":[],"error_patterns":[],"overall_mastery":1.0,"summary":"全对！","suggestion":""},"error":None}
    text = "\n---\n".join(f"题号:{e.get('question_index','?')}\n题干:{e.get('stem','')}\n知识点:{e.get('knowledge_point','')}\n正确答案:{e.get('correct_answer','')}\n用户答案:{e.get('user_answer','')}\n反馈:{e.get('feedback','')}" for e in errors)
    r = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":f"以下错题请分析：\n{text}\n错题数：{len(errors)}/{total}"}], ErrorAnalysisReport)
    return {"type":"errors_analyzed","payload":{"exam_id":eid,**r.model_dump()},"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"error-analyzer"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8007)
