"""Agent ⑥ 判题 — 规则+LLM 混合。"""
from fastapi import FastAPI
from llm import chat_structured
from models import GradingResult

SYSTEM = "判题。选择题/判断题直接比对；填空题语义匹配；简答/论述按得分点评分。"
app = FastAPI(title="Grader")

def _rule(q, t, a, i):
    e = str(q.get("correct_index","")) if t=="choice" else str(q.get("judgment",""))
    c = a.strip()==e if t=="choice" else a.strip().lower()==e.lower()
    return GradingResult(question_index=i, is_correct=c, score=100.0 if c else 0.0, max_score=100.0, feedback="" if c else f"正确答案：{_ext(q)}")

def _fill(q, a, i):
    for x in q.get("answers",[]):
        if x.lower() in a.lower() or a.lower() in x.lower(): return GradingResult(question_index=i, is_correct=True, score=100.0, max_score=100.0, feedback="正确！")
    return GradingResult(question_index=i, is_correct=False, score=0.0, max_score=100.0, feedback=f"可接受：{' / '.join(q.get('answers',[]))}")

def _ext(q):
    if "correct_index" in q: return f"选项 {chr(65+q['correct_index'])}"
    if "judgment" in q: return str(q["judgment"])
    if "answers" in q: return " / ".join(q["answers"])
    return q.get("reference_answer","") or q.get("correct_answer","")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); q=p.get("question",{}); u=p.get("user_answer",{}); t=u.get("question_type",""); a=u.get("answer_text",""); i=u.get("question_index",0)
    if t in ("choice","judgment"): r=_rule(q,t,a,i)
    elif t=="fill_blank": r=_fill(q,a,i)
    else: r=await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":f"类型：{t}\n题干：{q.get('stem','')}\n标准答案：{_ext(q)}\n得分点：{q.get('scoring_criteria',[]) or q.get('reference_answer','')}\n用户答案：{a}"}],GradingResult)
    return {"type":"answer_graded","payload":r.model_dump(),"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"grader"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8006)
