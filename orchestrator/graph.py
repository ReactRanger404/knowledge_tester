"""LangGraph — 编排 7 个独立 Agent 微服务。"""
from __future__ import annotations
import os, uuid, asyncio, json
from datetime import datetime
from typing import TypedDict, Optional, Literal
import aiohttp
from langgraph.graph import StateGraph, END, START
from orchestrator.models import ExamPaper, GradingReport, GradingResult, ErrorAnalysisReport
from orchestrator.models import ChoiceQuestion, JudgmentQuestion, FillBlankQuestion, ShortAnswerQuestion, EssayQuestion
from rag.vector_store import get_store

AGENTS = {
    "kp": os.getenv("AGENT_KP","http://knowledge-extractor:8000") if os.getenv("DOCKER") else os.getenv("AGENT_KP","http://localhost:8001"),
    "qg": os.getenv("AGENT_QG","http://question-generator:8000") if os.getenv("DOCKER") else os.getenv("AGENT_QG","http://localhost:8002"),
    "ta": os.getenv("AGENT_TA","http://type-adapter:8000") if os.getenv("DOCKER") else os.getenv("AGENT_TA","http://localhost:8003"),
    "qr": os.getenv("AGENT_QR","http://quality-reviewer:8000") if os.getenv("DOCKER") else os.getenv("AGENT_QR","http://localhost:8004"),
    "ec": os.getenv("AGENT_EC","http://exam-composer:8000") if os.getenv("DOCKER") else os.getenv("AGENT_EC","http://localhost:8005"),
    "gr": os.getenv("AGENT_GR","http://grader:8000") if os.getenv("DOCKER") else os.getenv("AGENT_GR","http://localhost:8006"),
    "ea": os.getenv("AGENT_EA","http://error-analyzer:8000") if os.getenv("DOCKER") else os.getenv("AGENT_EA","http://localhost:8007"),
}
TIMEOUT = 180.0

async def _call(name: str, body: dict) -> dict | list:
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=TIMEOUT),
        connector=aiohttp.TCPConnector(force_close=True),
    ) as session:
        async with session.post(f"{AGENTS[name]}/message", json=body) as r:
            r.raise_for_status()
            return await r.json()

# ═══════════════════════════════════ 出题图 ═══════════════════

class ExamState(TypedDict):
    config: dict; knowledge_points: list
    formatted_pool: list; pending_review: list
    exam_paper: Optional[dict]; error: Optional[str]

def _route(state: ExamState) -> Literal["batch_review", "compose_exam"]:
    return "batch_review" if state.get("pending_review") else "compose_exam"

async def extract_knowledge(state: ExamState) -> dict:
    cfg = state["config"]
    t0 = __import__('time').time()
    r = await _call("kp", {"type": "extract_knowledge", "payload": {"source_material": cfg["source_material"]}})
    kps = r.get("payload", {}).get("knowledge_points", [])
    print(f"[计时] 知识点提取: {len(kps)} 个, 耗时 {__import__('time').time()-t0:.0f}s")
    return {"knowledge_points": kps}

async def generate_questions(state: ExamState) -> dict:
    """每个知识点出一道题，不够时轮询复用（换难度避免雷同）。"""
    kps = state["knowledge_points"]
    types = state["config"].get("question_types", ["choice"])
    total = state["config"].get("total_count", 10)
    kb_name = state["config"].get("kb_name", "")
    diffs = ["easy", "medium", "hard"]

    # 按重要度取前 needed 个 KP，不够就轮询
    needed = min(total, len(kps))
    if len(kps) > needed:
        kps = sorted(kps, key=lambda k: k.get("importance", 0), reverse=True)[:needed]

    # 多生成一些，给审核留余量（保证各种题型都能通过审核）
    gen_count = max(total, int(total * 1.8))
    pairs = []
    for i in range(gen_count):
        kp = kps[i % len(kps)]
        tt = types[i % len(types)]
        dd = diffs[i % len(diffs)]
        pairs.append((kp, tt, dd))

    async def _gen(kp, ttype, diff):
        t0 = __import__('time').time()
        context = ""
        if kb_name:
            try:
                store = get_store()
                results = await store.search(kp.get("concept", ""), top_k=2, doc_name=kb_name)
                context = "\n".join(r["text"][:500] for r in results)
            except Exception:
                pass
        r = await _call("qg", {"type": "generate_question", "payload": {
            "knowledge_point": kp.get("concept", ""), "context": context,
            "importance": kp.get("importance", 0.5), "difficulty": diff,
            "target_type": ttype}})
        raw = r.get("payload", {}).get("raw_question", {})
        if not raw:
            return None
        ta = await _call("ta", {"type": "adapt_type", "payload": {"raw_question": raw, "target_type": ttype}})
        fmt = ta.get("payload", {}).get("formatted_question", {})
        if fmt:
            print(f"[计时] 「{kp.get('concept','')[:16]}」{diff}→{ttype}: {__import__('time').time()-t0:.0f}s")
        return fmt if fmt else None

    t0 = __import__('time').time()
    results = await asyncio.gather(*[_gen(kp, t, d) for kp, t, d in pairs], return_exceptions=True)
    pending = [r for r in results if isinstance(r, dict) and r]
    print(f"[计时] 出题总耗时: {__import__('time').time()-t0:.0f}s, 共 {len(pending)} 道")
    return {"pending_review": pending}

CHUNK_SIZE = 10

async def batch_review(state: ExamState) -> dict:
    pending = list(state.get("pending_review", []))
    if not pending:
        return {"pending_review": []}
    pool = list(state["formatted_pool"])
    t0 = __import__('time').time()
    for chunk_start in range(0, len(pending), CHUNK_SIZE):
        chunk = pending[chunk_start:chunk_start + CHUNK_SIZE]
        r = await _call("qr", {"type": "review_batch", "payload": {"questions": chunk}})
        reviews = r.get("payload", {}).get("reviews", [])
        passed = 0
        for i, rv in enumerate(reviews):
            if rv.get("verdict") == "pass" and i < len(chunk):
                pool.append(chunk[i])
                passed += 1
        print(f"[计时] 批量审核: {len(chunk)} 题, 通过 {passed}, 耗时 {__import__('time').time()-t0:.0f}s")
    print(f"[计时] 审核总耗时: {__import__('time').time()-t0:.0f}s, 池中 {len(pool)} 题")
    return {"pending_review": [], "formatted_pool": pool}

async def compose_exam(state: ExamState) -> dict:
    pool = state["formatted_pool"]; cfg = state["config"]
    types = cfg.get("question_types",["choice"]); total = cfg.get("total_count",10)
    if not pool:
        # 池子为空 → 返回错误而非崩溃
        return {"exam_paper": None, "error": "题库为空，无法组卷"}
    n=len(types); b=total//n if n else total; rem=total%n if n else 0
    tc = {t:b+(1 if i<rem else 0) for i,t in enumerate(types)}
    ec = await _call("ec",{"type":"compose_exam","payload":{"question_pool":pool,"type_counts":tc,"total_count":min(total, len(pool))}})
    comp = ec.get("payload",{}); sel = comp.get("selected_indices",[])
    tm = {"choice":ChoiceQuestion,"judgment":JudgmentQuestion,"fill_blank":FillBlankQuestion,"short_answer":ShortAnswerQuestion,"essay":EssayQuestion}
    qs = []
    for i in sel:
        if i<len(pool):
            qd=pool[i]; m=tm.get(qd.get("type",""))
            if m:
                try: qs.append(m.model_validate(qd))
                except: qs.append(qd)
            else: qs.append(qd)
    if not qs:
        return {"exam_paper": None, "error": "组卷后无有效题目"}
    paper = ExamPaper(id=str(uuid.uuid4())[:8],title=f"测验-{datetime.now().strftime('%m-%d %H:%M')}",questions=qs,question_count=len(qs),
        difficulty_summary=comp.get("difficulty_summary",{}),knowledge_coverage=comp.get("knowledge_points",[]))
    return {"exam_paper":paper.model_dump(mode="json")}

def build_exam_graph():
    g = StateGraph(ExamState)
    g.add_node("extract_knowledge", extract_knowledge)
    g.add_node("generate_questions", generate_questions)
    g.add_node("batch_review", batch_review)
    g.add_node("compose_exam", compose_exam)
    g.add_edge(START, "extract_knowledge")
    g.add_edge("extract_knowledge", "generate_questions")
    g.add_conditional_edges("generate_questions", _route, {
        "batch_review": "batch_review", "compose_exam": "compose_exam"})
    g.add_edge("batch_review", "compose_exam")
    g.add_edge("compose_exam", END)
    return g.compile()

# ═══════════════════════════════════ 判题图 ═══════════════════

class GradeState(TypedDict):
    exam_paper: dict; user_answers: list; results: list; question_index: int
    grading_report: Optional[dict]; error_analysis: Optional[dict]; error: Optional[str]

def _grade_route(state: GradeState) -> Literal["grade_single","analyze_errors"]:
    return "grade_single" if state["question_index"] < state["exam_paper"]["question_count"] else "analyze_errors"

async def grade_single(state: GradeState) -> dict:
    i=state["question_index"]; q=state["exam_paper"]["questions"][i]
    um={ua.get("question_index",0):ua for ua in state["user_answers"]}; ua=um.get(i,{"answer_text":"","question_index":i,"question_type":q.get("type","")})
    r=await _call("gr",{"type":"grade_answer","payload":{"question":q,"user_answer":ua}})
    res=list(state.get("results",[]))+[r.get("payload",{})]
    return {"results":res,"question_index":i+1}

async def analyze_errors(state: GradeState) -> dict:
    res=state.get("results",[]); qs=state["exam_paper"]["questions"]; um={ua.get("question_index",0):ua for ua in state["user_answers"]}
    correct=sum(1 for r in res if r.get("is_correct"))
    report=GradingReport(exam_id=state["exam_paper"]["id"],total_questions=len(res),correct_count=correct,
        total_score=sum(r.get("score",0) for r in res),max_total_score=sum(r.get("max_score",100) for r in res),
        results=[GradingResult(**r) for r in res])
    errors=[]
    for r,qd in zip(res,qs):
        if r.get("is_correct"): continue
        ua=um.get(r.get("question_index",0),{})
        def _e(q):
            if "correct_index" in q: return f"{chr(65+q['correct_index'])}"
            if "judgment" in q: return str(q["judgment"])
            if "answers" in q: return " / ".join(q["answers"])
            return q.get("reference_answer","") or q.get("correct_answer","")
        errors.append({"question_index":r["question_index"],"stem":qd.get("stem",""),"knowledge_point":qd.get("knowledge_point",""),
            "difficulty":str(qd.get("difficulty","")),"correct_answer":_e(qd),"user_answer":ua.get("answer_text","未作答"),"feedback":r.get("feedback","")})
    out={"grading_report":report.model_dump(mode="json")}
    if errors:
        ea=await _call("ea",{"type":"analyze_errors","payload":{"exam_id":state["exam_paper"]["id"],"error_details":errors,"total_count":len(qs)}})
        out["error_analysis"]=ea.get("payload",{})
    return out

def build_grading_graph():
    g=StateGraph(GradeState)
    g.add_node("grade_single",grade_single); g.add_node("analyze_errors",analyze_errors)
    g.add_edge(START,"grade_single")
    g.add_conditional_edges("grade_single",_grade_route,{"grade_single":"grade_single","analyze_errors":"analyze_errors"})
    g.add_edge("analyze_errors",END)
    return g.compile()
