"""Agent ⑦ 错题分析。"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi import FastAPI
from llm import chat_structured
from models import ErrorAnalysisReport

SYSTEM = """你是一个知识点讲解助手。请针对每道题目，提取并讲解题目所考察的知识点。

要求：
- 严格依据题干的描述或选项内容，不能引入题干未提及的知识
- 知识点的讲解要简明扼要、准确
- 每个知识点要直接关联到具体的题干内容
- **question_index 必须是单个整数**（题号），不能是字符串、列表或范围
- 如果多道题考察同一个知识点，每条记录只写一道题，拆成多条（不能合并写到一个 question_index 里）

必须返回 JSON，格式如下：
{
  "knowledge_explanations": [
    {
      "question_index": 0,
      "knowledge_point": "知识点名称",
      "explanation": "基于题干/选项的知识点讲解，用中文"
    }
  ]
}
knowledge_explanations 不能为空。"""
app = FastAPI(title="Error Analyzer")

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); errors = p.get("error_details",[]); total = p.get("total_count",0); eid = p.get("exam_id","")
    if not errors:
        return {"type":"errors_analyzed","payload":{"exam_id":eid,"knowledge_explanations":[]},"error":None}
    text = "\n---\n".join(f"题号:{e.get('question_index','?')}\n题干:{e.get('stem','')}\n知识点:{e.get('knowledge_point','')}\n正确答案:{e.get('correct_answer','')}\n用户答案:{e.get('user_answer','')}\n反馈:{e.get('feedback','')}" for e in errors)
    r = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":f"以下错题请分析：\n{text}\n错题数：{len(errors)}/{total}"}], ErrorAnalysisReport)
    return {"type":"errors_analyzed","payload":{**r.model_dump(), "exam_id": eid},"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"error-analyzer"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8007)
