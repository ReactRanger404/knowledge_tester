import os, re, asyncio
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
_client = None
_lock = asyncio.Lock()
async def _c():
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = AsyncOpenAI(api_key=os.getenv("LLM_API_KEY",""), base_url=os.getenv("LLM_BASE_URL","https://api.deepseek.com/v1"), http_client=httpx.AsyncClient(proxy=None, trust_env=False))
    return _client
async def chat_structured(messages, resp_model, temperature=0.2, retry=1):
    for m in messages:
        if m["role"] == "system": m["content"] += "\n\n输出纯 JSON。"
    for attempt in range(retry + 1):
        client = await _c()
        r = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL_GR", os.getenv("LLM_MODEL", "deepseek-v4-flash")),
            messages=messages, temperature=temperature, response_format={"type":"json_object"},
        )
        c = r.choices[0].message.content or ""
        c = c.strip()
        if c.startswith("```"): c = re.sub(r"^```(?:json)?\s*","",c); c = re.sub(r"\s*```$","",c)
        i = c.find("{"); c = c[i:c.rfind("}")+1] if i>=0 else c
        try:
            return resp_model.model_validate_json(c)
        except Exception as e:
            if attempt < retry:
                messages = messages + [{"role":"assistant","content":c},{"role":"user","content":f"JSON 解析错误：{e}。请重新输出符合格式要求的 JSON。"}]
                continue
            raise
