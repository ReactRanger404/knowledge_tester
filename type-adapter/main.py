"""Agent ③ 题型适配 — tool calling + JSON 双保险。"""
from fastapi import FastAPI
from llm import chat_structured, chat_with_tool
from models import ChoiceQuestion, JudgmentQuestion, FillBlankQuestion, ShortAnswerQuestion, EssayQuestion

TYPE_MAP = {"choice": ChoiceQuestion, "judgment": JudgmentQuestion, "fill_blank": FillBlankQuestion, "short_answer": ShortAnswerQuestion, "essay": EssayQuestion}
TOOL_TYPES = {"choice", "judgment", "fill_blank"}

SYSTEM = """将原始题目转为指定题型。保持知识点、难度、解析不变。

转换规则：
- choice：用 correct_answer + distractors 组成 options，correct_index 指向正确选项
- judgment：根据 correct_answer 判断对错（True/False）
- fill_blank：题干中用____表示填空位置，correct_answer 放入 answers 列表
- short_answer：直接使用题干和答案，加 scoring_criteria
- essay：保留题干，展开参考答案为评分要点"""

app = FastAPI(title="Type Adapter")

def _rule_fallback(raw: dict, t: str):
    """LLM 失败时的规则兜底。"""
    if t == "fill_blank":
        stem = raw.get("stem","")
        ans = raw.get("correct_answer","")
        if "____" not in stem and ans:
            stem = stem.replace(ans, "____", 1) if ans in stem else stem + "（____）"
        return FillBlankQuestion(
            stem=stem, answers=[ans] if ans else ["（填写答案）"],
            difficulty=raw.get("difficulty","medium"), knowledge_point=raw.get("knowledge_point",""),
            explanation=raw.get("explanation",""),
        )
    return None

@app.post("/message")
async def handle(body: dict):
    p = body.get("payload",{}); raw = p.get("raw_question",{}); t = p.get("target_type","choice")
    m = TYPE_MAP.get(t)
    if not m: return {"type":"error","payload":{},"error":f"unsupported: {t}"}

    user_msg = f"转为「{t}」题型：\n题干：{raw.get('stem','')}\n答案：{raw.get('correct_answer','')}\n干扰项：{', '.join(raw.get('distractors',[]))}\n知识点：{raw.get('knowledge_point','')}\n难度：{raw.get('difficulty','medium')}"
    result = None

    # ① tool calling
    if t in TOOL_TYPES:
        tool_data = await chat_with_tool([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg}
        ], t)
        if tool_data:
            try: result = m.model_validate({**tool_data, "type": t})
            except Exception: pass

    # ② JSON fallback
    if result is None:
        try: result = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":user_msg}], m)
        except Exception: pass

    # ③ 规则兜底
    if result is None:
        result = _rule_fallback(raw, t)

    if result is None:
        return {"type":"type_adapted","payload":{"formatted_question":{}},"error":"all methods failed"}

    return {"type":"type_adapted","payload":{"formatted_question":result.model_dump(),"knowledge_point":raw.get("knowledge_point","")},"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"type-adapter"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8003)
