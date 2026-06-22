"""Agent ⑤ 组卷编排 — 纯逻辑，无 LLM 调用。"""
import os, random
from collections import Counter
from fastapi import FastAPI

app = FastAPI(title="Exam Composer")

def _type(q):
    t = q.get("type","")
    return t.lower().replace("question","").strip() if isinstance(t,str) else str(t)

def _compose(pool, type_counts, total):
    if not pool: return {"selected_indices":[],"type_summary":{},"difficulty_summary":{},"knowledge_points":[],"shortfall":total}
    random.seed(42); idx = list(range(len(pool))); random.shuffle(idx)
    by_type = {}
    for i in idx: by_type.setdefault(_type(pool[i]),[]).append(i)
    sel, used = [], set()
    for t in ["choice","judgment","fill_blank","short_answer","essay"]:
        need = type_counts.get(t,0); avail = by_type.get(t,[]); picked = 0
        for i in avail:
            if picked >= need: break
            kp = pool[i].get("knowledge_point","")
            if kp and sum(1 for s in sel if pool[s].get("knowledge_point","")==kp) >= 2: continue
            sel.append(i); used.add(kp); picked += 1
    short = max(0, total - len(sel))
    sel.sort(key=lambda i: {"easy":0,"medium":1,"hard":2}.get(pool[i].get("difficulty","medium"),1))
    ts, ds, kps = Counter(), Counter(), set()
    for i in sel:
        q = pool[i]; ts[_type(q)]+=1; ds[q.get("difficulty","medium")]+=1
        if q.get("knowledge_point"): kps.add(q["knowledge_point"])
    return {"selected_indices":sel,"type_summary":dict(ts),"difficulty_summary":dict(ds),"knowledge_points":list(kps),"shortfall":short}

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); pool = p.get("question_pool",[]); tc = p.get("type_counts",{}); total = p.get("total_count",10)
    return {"type":"exam_composed","payload":_compose(pool,tc,total),"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"exam-composer"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8005)
