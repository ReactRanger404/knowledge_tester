"""LLM 客户端 — 题型适配专用，tool calling + JSON 双保险。"""
import os, re, sys, asyncio, json as _json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
from tools import TA_TOOLS

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

async def chat_with_tool(messages, target_type: str, temperature=0.3):
    """用 tool calling 让 LLM 输出指定题型的结构化数据。"""
    tool_def = TA_TOOLS.get(target_type)
    if not tool_def:
        return None
    client = await _c()
    try:
        r = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL_TA", os.getenv("LLM_MODEL", "deepseek-v4-flash")),
            messages=messages, temperature=temperature,
            tools=[tool_def],
            tool_choice={"type": "function", "function": {"name": tool_def["function"]["name"]}},
        )
        msg = r.choices[0].message
        if msg.tool_calls:
            return _json.loads(msg.tool_calls[0].function.arguments)
        print(f"[TA] tool calling 未返回 tool_calls, content={msg.content[:100] if msg.content else '空'}")
        return None
    except Exception as e:
        print(f"[TA] tool calling 异常: {e}")
        return None
