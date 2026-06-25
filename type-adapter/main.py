"""Agent ③ 题型适配 — tool calling + JSON + 规则三保险。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi import FastAPI
from llm import chat_structured, chat_with_tool
from models import ChoiceQuestion, JudgmentQuestion, FillBlankQuestion, ShortAnswerQuestion, EssayQuestion

TYPE_MAP = {"choice": ChoiceQuestion, "judgment": JudgmentQuestion, "fill_blank": FillBlankQuestion, "short_answer": ShortAnswerQuestion, "essay": EssayQuestion}
TOOL_TYPES = {"choice", "judgment", "fill_blank"}

SYSTEM = """将原始题目转为指定题型。保持知识点、难度、解析不变。

转换规则：
- choice：用 correct_answer + distractors 组成 options，correct_index 指向正确选项
- judgment：根据 correct_answer 判断对错（True/False）
- fill_blank：题干中用____表示填空位置，correct_answer 放入 answers 列表"""

app = FastAPI(title="Type Adapter")

def _ensure_explanation(expl: str, stem: str, ans: str) -> str:
    """保证 explanation 不为空。"""
    if expl and len(expl) > 5:
        return expl
    return f"正确答案：{ans[:50]}。{stem[:60]}"

def _rule_fallback(raw: dict, t: str):
    """全部题型的规则兜底（LLM 和 tool 都失败时用）。"""
    stem, kp, diff, expl = raw.get("stem",""), raw.get("knowledge_point",""), raw.get("difficulty","medium"), raw.get("explanation","")
    ans, dist = raw.get("correct_answer",""), raw.get("distractors",[])
    expl = _ensure_explanation(expl, stem, ans)

    if t == "choice" and dist and ans:
        opts = dist + [ans]
        import random; random.shuffle(opts)
        return ChoiceQuestion(stem=stem, options=opts, correct_index=opts.index(ans), difficulty=diff, knowledge_point=kp, explanation=expl)

    if t == "judgment" and ans:
        return JudgmentQuestion(stem=stem, judgment=ans.strip().lower() in ("正确","对","true","是","yes"), difficulty=diff, knowledge_point=kp, explanation=expl)

    if t == "fill_blank":
        s = stem
        if "____" not in s and ans:
            s = s.replace(ans, "____", 1) if ans in s else s + "（____）"
        return FillBlankQuestion(stem=s, answers=[ans] if ans else ["（填写答案）"], difficulty=diff, knowledge_point=kp, explanation=expl)

    if t == "short_answer":
        return ShortAnswerQuestion(stem=stem, reference_answer=ans, scoring_criteria=[ans] if ans else [], difficulty=diff, knowledge_point=kp, explanation=expl)

    if t == "essay":
        return EssayQuestion(stem=stem, reference_answer=ans, scoring_criteria=[ans] if ans else [], difficulty=diff, knowledge_point=kp, explanation=expl)

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
        try:
            tool_data = await chat_with_tool([{"role":"system","content":SYSTEM},{"role":"user","content":user_msg}], t)
            if tool_data:
                result = m.model_validate({**tool_data, "type": t})
        except Exception as e:
            print(f"[TA] tool 验证失败: {e}")

    # ② JSON fallback
    if result is None:
        try: result = await chat_structured([{"role":"system","content":SYSTEM},{"role":"user","content":user_msg}], m)
        except Exception: pass

    # ③ 规则兜底（确保不返回 0 题）
    if result is None:
        result = _rule_fallback(raw, t)

    if result is None:
        return {"type":"type_adapted","payload":{"formatted_question":{}},"error":f"all methods failed for {t}"}

    return {"type":"type_adapted","payload":{"formatted_question":result.model_dump(),"knowledge_point":raw.get("knowledge_point","")},"error":None}

@app.get("/health")
async def health():
    return {"status":"ok","name":"type-adapter"}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8003)
