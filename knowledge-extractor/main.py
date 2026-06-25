"""Agent ① 知识点提取。"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from contextlib import asynccontextmanager
from fastapi import FastAPI
from llm import chat_structured
from models import KnowledgeExtractionResult

SYSTEM = """你是知识点提取专家。从教材原文中提取适合出题的知识点原子。
要求：
- 每个知识点必须具体可考（如"TCP三次握手"可以，"网络协议概论"太宽泛不行）
- 知识点之间不要重复，同义合并
- 标注重要度 0~1（核心考点 0.8+，一般内容 0.5-0.7，边缘知识 0.3-）
- 每个知识点给 2-3 个关键词
- **只提取最重要的知识点，数量控制在 8-12 个**

返回 JSON：
{"knowledge_points": [{"concept": "TCP三次握手", "importance": 0.9, "keywords": ["SYN", "ACK", "连接建立"]}]}"""

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
