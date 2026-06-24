"""Agent ① 知识点提取 — 完全自包含。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from llm import chat_structured
from models import KnowledgeExtractionResult

SYSTEM = """你是一个专业的知识点提取专家。
从资料中提取可出题的知识点原子，每个知识点对应一道题。
标注重要度 0~1。

请严格返回以下 JSON 格式：
{"knowledge_points": [{"concept": "知识点名", "importance": 0.8, "keywords": ["关键词"]}]}"""

app = FastAPI(title="Knowledge Extractor")

@app.post("/message")
async def handle(body: dict):
    src = body.get("payload", {}).get("source_material", "")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"从以下资料提取知识点：\n\n{src}"},
    ]
    try:
        result = await chat_structured(messages, KnowledgeExtractionResult)
    except Exception as e:
        return {"type": "knowledge_extracted", "payload": {"knowledge_points":[]}, "error": str(e)}
    if result is None:
        return {"type": "knowledge_extracted", "payload": {"knowledge_points":[]}, "error": "LLM returned empty"}
    return {"type": "knowledge_extracted", "payload": result.model_dump(), "error": None}

@app.get("/health")
async def health():
    return {"status": "ok", "name": "knowledge-extractor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
