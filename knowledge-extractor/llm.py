"""LLM 客户端 — 该 Agent 独享，可独立换模型。"""
import os, re
from openai import AsyncOpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        )
    return _client

def _model() -> str:
    return os.getenv("LLM_MODEL_KP", os.getenv("LLM_MODEL", "deepseek-v4-flash"))

async def chat_structured(messages: list, resp_model: type, temperature=0.3):
    for m in messages:
        if m["role"] == "system":
            m["content"] += "\n\n输出必须是纯 JSON 对象，不要 markdown 代码块。"
            break
    client = _get_client()
    resp = await client.chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or ""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    brace = content.find("{")
    if brace >= 0:
        content = content[brace : content.rfind("}") + 1]
    return resp_model.model_validate_json(content)
