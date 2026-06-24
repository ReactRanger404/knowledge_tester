"""LLM 客户端 — 该 Agent 独享，可独立换模型。"""
import os, re, asyncio, json as _json
import httpx
from openai import AsyncOpenAI

_client = None
_lock = asyncio.Lock()

async def _get_client():
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = AsyncOpenAI(
                    api_key=os.getenv("LLM_API_KEY", ""),
                    base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
                    http_client=httpx.AsyncClient(proxy=None, trust_env=False),
                )
    return _client

def _model() -> str:
    return os.getenv("LLM_MODEL_KP", os.getenv("LLM_MODEL", "deepseek-v4-flash"))

async def chat_structured(messages: list, resp_model: type, temperature=0.3):
    for m in messages:
        if m["role"] == "system":
            m["content"] += "\n\n输出必须是纯 JSON 对象，不要 markdown 代码块。"
            break
    client = await _get_client()
    resp = await client.chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or ""
    content = content.strip()
    if not content:
        return None
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    brace = content.find("{")
    if brace >= 0:
        content = content[brace : content.rfind("}") + 1]
    try:
        return resp_model.model_validate_json(content)
    except Exception:
        try:
            d = _json.loads(content)
            return resp_model.model_validate(d)
        except Exception:
            return None
