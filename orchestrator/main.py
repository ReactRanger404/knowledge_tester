"""Orchestrator — FastAPI + LangGraph 编排后端。"""
import sys, os, json, subprocess, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orchestrator.models import ExamConfig, UserAnswer, ExamPaper
from orchestrator.graph import build_exam_graph, build_grading_graph
from rag.vector_store import get_store, auto_index_kb

_exam_graph = _grading_graph = None
_exam_store: dict[str, dict] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _exam_graph, _grading_graph
    _exam_graph = build_exam_graph()
    _grading_graph = build_grading_graph()
    # 启动时自动索引知识库
    print("[RAG] 检查知识库...")
    indexed = await auto_index_kb()
    if indexed:
        for r in indexed:
            print(f"  + {r['name']} ({r['chunks']} 块)")
    print("[RAG] 就绪")
    yield

app = FastAPI(title="Knowledge Tester API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 前端静态文件
dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=os.path.join(dist,"assets")), name="assets")
    from fastapi.responses import FileResponse
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(dist,"index.html"))
    @app.exception_handler(404)
    async def spa_fallback(req, exc):
        return FileResponse(os.path.join(dist,"index.html"))

@app.post("/api/exam/generate")
async def api_generate(config: ExamConfig):
    # 如果指定了知识库名称，从块存储加载内容
    if config.kb_name and not config.source_material:
        store = get_store()
        docs = await store.get_documents()
        if config.kb_name not in [d["name"] for d in docs]:
            kb_path = os.path.join(KB_DIR, config.kb_name, "content.txt")
            if os.path.isfile(kb_path):
                with open(kb_path, "r", encoding="utf-8") as f:
                    config.source_material = f.read()
                print(f"[kb] 从文件加载「{config.kb_name}」")
            else:
                return {"error": f"知识库「{config.kb_name}」不存在"}
        else:
            config.source_material = await store.get_text_for_exam(config.kb_name)
            total = await store.get_chunk_count(config.kb_name)
            print(f"[RAG] 加载「{config.kb_name}」({len(config.source_material)} 字符, 共 {total} 块)")

    if not config.source_material.strip():
        return {"error": "请提供 source_material 或指定 kb_name"}

    state = await _exam_graph.ainvoke({
        "config": config.model_dump(mode="json"), "knowledge_points": [],
        "question_queue": [], "formatted_pool": [], "pending_review": [],
        "exam_paper": None, "error": None,
    }, {"recursion_limit": 100})
    paper = state.get("exam_paper")
    if paper: _exam_store[paper["id"]] = paper
    return paper or {"error": "出题失败"}

@app.post("/api/exam/{exam_id}/submit")
async def api_submit(exam_id: str, answers: list[UserAnswer]):
    paper_dict = _exam_store.get(exam_id)
    if not paper_dict: return {"error": "试卷不存在"}
    paper = ExamPaper.model_validate(paper_dict)
    state = await _grading_graph.ainvoke({
        "exam_paper": paper.model_dump(mode="json"),
        "user_answers": [a.model_dump(mode="json") for a in answers],
        "results": [], "question_index": 0,
        "grading_report": None, "error_analysis": None, "error": None,
    })
    return {"grading_report": state.get("grading_report"), "error_analysis": state.get("error_analysis")}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}

# ── 知识库 API ────────────────────────────────────────

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb")

@app.get("/api/kb")
async def list_kb():
    """列出知识库所有教材（含索引信息）。"""
    store = get_store()
    docs = await store.get_documents()
    for d in docs:
        d["char_count"] = await store.get_char_count(d["name"])
    return docs

@app.get("/api/kb/{name}")
async def get_kb(name: str, preview: bool = False):
    """获取知识库全部内容。"""
    store = get_store()
    text = await store.get_full_text(name) if not preview else await store.get_text_for_exam(name)
    if not text:
        return {"error": f"知识库「{name}」未索引"}
    char_count = await store.get_char_count(name)
    return {"name": name, "char_count": char_count, "text": text[:2000] if preview else text}

@app.get("/api/kb/{name}/chapters")
async def kb_chapters(name: str):
    """获取章节列表。"""
    store = get_store()
    chapters = await store.get_chapters(name)
    total = await store.get_chunk_count(name)
    return {"name": name, "chapters": chapters, "total_chunks": total}

@app.post("/api/kb/reindex")
async def reindex_kb():
    """重建索引。"""
    store = get_store()
    await auto_index_kb()
    docs = await store.get_documents()
    return {"total_docs": len(docs), "docs": docs}

if __name__ == "__main__":
    import httpx, uvicorn
    BASE = os.path.dirname(os.path.dirname(__file__))
    AGENTS = [
        ("knowledge-extractor",8001), ("question-generator",8002),
        ("type-adapter",8003), ("quality-reviewer",8004),
        ("exam-composer",8005), ("grader",8006), ("error-analyzer",8007),
    ]
    print("="*40+"\n  Knowledge Tester 启动中...\n"+"="*40)
    for name,port in AGENTS:
        subprocess.Popen([sys.executable,"main.py"],cwd=os.path.join(BASE,name),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform=="win32" else 0)
        time.sleep(0.3)
    def wait_all():
        for n,p in AGENTS:
            for _ in range(30):
                try:
                    if httpx.get(f"http://localhost:{p}/health",timeout=2).status_code==200: break
                except: time.sleep(0.5)
            print(f"  ✅ {n} (:p)")
    threading.Thread(target=wait_all).start()
    print(f"\n  🎯 http://localhost:8000\n"+"="*40)
    uvicorn.run(app, host="0.0.0.0", port=8000)
