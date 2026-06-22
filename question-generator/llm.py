"""LLM 客户端 — 可独立配置环境变量 LLM_MODEL_QG 来换模型。"""
import os, re
from openai import AsyncOpenAI

_client = None
def _client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("LLM_API_KEY",""), base_url=os.getenv("LLM_BASE_URL","https://api.deepseek.com/v1"))
    return _client

async def chat_structured(messages, resp_model, temperature=0.4):
    for m in messages:
        if m["role"] == "system":
            m["content"] += "\n\n输出纯 JSON，不要代码块。"
            break
    r = await _client().chat.completions.create(
        model=os.getenv("LLM_MODEL_QG", os.getenv("LLM_MODEL", "deepseek-v4-flash")),
        messages=messages, temperature=temperature,
        response_format={"type": "json_object"},
    )
    c = r.choices[0].message.content or ""
    c = c.strip()
    if c.startswith("```"): c = re.sub(r"^```(?:json)?\s*", "", c); c = re.sub(r"\s*```$", "", c)
    i = c.find("{"); c = c[i:c.rfind("}")+1] if i>=0 else c
    return resp_model.model_validate_json(c)
