import os, re, asyncio, json as _json
import httpx
from openai import AsyncOpenAI
_client = None
_lock = asyncio.Lock()
async def _c():
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = AsyncOpenAI(api_key=os.getenv("LLM_API_KEY",""), base_url=os.getenv("LLM_BASE_URL","https://api.deepseek.com/v1"), http_client=httpx.AsyncClient(proxy=None, trust_env=False))
    return _client
async def chat_structured(messages, resp_model, temperature=0.3):
    for m in messages:
        if m["role"] == "system": m["content"] += "\n\n输出纯 JSON。"
    client = await _c()
    r = await client.chat.completions.create(
        model=os.getenv("LLM_MODEL_TA", os.getenv("LLM_MODEL", "deepseek-v4-flash")),
        messages=messages, temperature=temperature, response_format={"type":"json_object"},
    )
    c = r.choices[0].message.content or ""
    c = c.strip()
    if not c: return None
    if c.startswith("```"): c = re.sub(r"^```(?:json)?\s*","",c); c = re.sub(r"\s*```$","",c)
    i = c.find("{")
    if i >= 0:
        c = c[i:]; depth, end = 0, 0
        for j, ch in enumerate(c):
            if ch == "{": depth += 1
            elif ch == "}": depth -= 1
            if depth == 0: end = j + 1; break
        if end: c = c[:end]
    try:
        return resp_model.model_validate_json(c)
    except Exception:
        try:
            d = _json.loads(c)
            return resp_model.model_validate(d)
        except Exception:
            return None
