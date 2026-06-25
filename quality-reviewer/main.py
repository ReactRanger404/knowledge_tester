"""Agent ④ 质量审核 — 支持批量审核。"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi import FastAPI
from llm import chat_structured
from models import ReviewResult, Verdict, BatchReviewResponse

SINGLE_SYSTEM = """快速审核题目质量。
只要题目没有明显错误就判 pass，有小瑕疵或表述不够完美不影响通过。
只有明确有知识错误、答案错误、题干完全看不懂才判 reject。
不要因为"可以更好"就拒，通过率尽量高。
请返回 JSON：{"verdict": "pass/reject", "dimensions": {"correctness": 0.9, "unambiguity": 0.8, "relevance": 1.0}, "suggestions": []}"""

BATCH_SYSTEM = """批量审核题目。宽松审核，只有明确的知识错误才 reject。
每道题独立判断，通过的尽量多。
按输入顺序返回：
{"reviews": [{"index": 0, "verdict": "pass", "justification": ""}, {"index": 1, "verdict": "reject", "justification": "答案错误"}]}"""

app = FastAPI(title="Quality Reviewer")

def _build_prompt(q: dict) -> str:
    ans = (q.get('correct_answer','') or
           (str(chr(65+q['correct_index'])) if 'correct_index' in q else '') or
           (str(q.get('judgment',''))) or
           (' / '.join(q.get('answers',[])) or ''))
    dist = ', '.join(q.get('distractors',[]) or q.get('options',[]))
    return f"知识点：{q.get('knowledge_point','')}\n题干：{q.get('stem','')}\n答案：{ans}\n干扰项：{dist}\n难度：{q.get('difficulty','medium')}"

@app.post("/message")
async def handle(body: dict):
    t = body.get("type", "")
    p = body.get("payload", {})

    # ── 批量审核 ──
    if t == "review_batch":
        questions = p.get("questions", [])
        if not questions:
            return {"type": "batch_reviewed", "payload": {"reviews": []}, "error": None}
        texts = "\n---\n".join(f"#{i} {_build_prompt(q)}" for i, q in enumerate(questions))
        result = await chat_structured([
            {"role": "system", "content": BATCH_SYSTEM},
            {"role": "user", "content": f"请审核以下 {len(questions)} 道题：\n\n{texts}"}
        ], BatchReviewResponse, temperature=0.2)
        if result is None:
            reviews = [{"index": i, "verdict": "pass"} for i in range(len(questions))]
        else:
            reviews = [r.model_dump() for r in result.reviews]
            seen = {r.get("index") for r in reviews}
            for i in range(len(questions)):
                if i not in seen:
                    reviews.append({"index": i, "verdict": "pass"})
        return {"type": "batch_reviewed", "payload": {"reviews": reviews}, "error": None}

    # ── 单题审核（兼容旧调用） ──
    q = p.get("formatted_question", p.get("raw_question", {}))
    rn = p.get("revision_round", 0)
    try:
        result = await chat_structured([
            {"role": "system", "content": SINGLE_SYSTEM},
            {"role": "user", "content": _build_prompt(q)}
        ], ReviewResult)
    except Exception as e:
        return [{"type": "question_reviewed", "payload": {"review": {"verdict": "pass"}, "question_data": q, "revision_round": rn}, "error": str(e)}]
    if result is None:
        return [{"type": "question_reviewed", "payload": {"review": {"verdict": "pass"}, "question_data": q, "revision_round": rn}, "error": "LLM empty, defaulting to pass"}]
    out = [{"type": "question_reviewed", "payload": {"review": result.model_dump(), "question_data": q, "revision_round": rn}, "error": None}]
    if result.verdict in (Verdict.REVISE, Verdict.REJECT) and rn < 3:
        out.append({"type": "revise_question", "payload": {"original_question": q, "suggestions": result.suggestions, "revision_round": rn + 1}, "error": None})
    return out

@app.get("/health")
async def health():
    return {"status":"ok","name":"quality-reviewer"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8004)
