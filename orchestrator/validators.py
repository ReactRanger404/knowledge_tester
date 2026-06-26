"""内容级 Schema 校验 — 检测 LLM 胡乱输出，补充 Pydantic 类型校验之外的语义校验。"""

from __future__ import annotations
from typing import Optional

# 常见模板占位符，LLM 偶尔会忘记替换
_PLACEHOLDER_PATTERNS = [
    "{{", "}}", "[题目", "[题干", "[选项", "[填空",
    "{$", "${", "___", "（__",
    "请在此处", "待补充", "TODO",
]


def validate_question(q: dict) -> tuple[bool, Optional[str]]:
    """校验一道题的内容是否合理。

    Returns:
        (True, None) —— 通过
        (False, 原因) —— 未通过
    """
    qtype = q.get("type", "")
    stem = q.get("stem", "")

    # ── 通用校验 ──

    if not stem or not stem.strip():
        return False, "题干为空"

    if len(stem.strip()) < 5:
        return False, f"题干过短（{len(stem.strip())} 字），无法构成有效问题"

    if any(p in stem for p in _PLACEHOLDER_PATTERNS):
        return False, "题干包含模板占位符，疑似未填充"

    # ── 按题型校验 ──

    if qtype == "choice":
        return _validate_choice(q)
    elif qtype == "judgment":
        return _validate_judgment(q)
    elif qtype == "fill_blank":
        return _validate_fill_blank(q)
    elif qtype in ("short_answer", "essay"):
        return _validate_open_ended(q)
    else:
        return False, f"未知题型: {qtype}"


def _validate_choice(q: dict) -> tuple[bool, Optional[str]]:
    opts = q.get("options", [])
    if len(opts) < 2:
        return False, f"选项不足（{len(opts)} 个），选择题至少需要 2 个选项"

    stripped = [o.strip() for o in opts]
    if len(set(stripped)) < 2:
        return False, "所有选项内容完全重复"

    # 检测选项长度是否过短（单个字符的选项通常不合理）
    if all(len(o) <= 1 for o in stripped):
        return False, "所有选项均为单字符，内容过简"

    # 检测选项是否包含模板残留
    for i, o in enumerate(stripped):
        if any(p in o for p in _PLACEHOLDER_PATTERNS):
            return False, f"选项 {chr(65+i)} 包含模板占位符"

    ci = q.get("correct_index", -1)
    if not isinstance(ci, int) or ci < 0 or ci >= len(opts):
        return False, f"correct_index（{ci}）超出选项范围（0~{len(opts)-1}）"

    return True, None


def _validate_judgment(q: dict) -> tuple[bool, Optional[str]]:
    judgment = q.get("judgment")
    if not isinstance(judgment, bool):
        return False, f"judgment 应为布尔值，实际为 {type(judgment).__name__}"

    # 判断题题干不能是问句格式
    stem = q.get("stem", "").strip()
    if stem.endswith("?") or stem.endswith("？"):
        return False, "判断题题干为问句格式，应改为陈述句"

    return True, None


def _validate_fill_blank(q: dict) -> tuple[bool, Optional[str]]:
    stem = q.get("stem", "")
    # 检查是否有填空标记（____ 或 ___ 或 __）
    if "____" not in stem and "___" not in stem and "__" not in stem and "（）" not in stem and "()" not in stem:
        return False, "填空题题干缺少填空标记（____）"

    answers = q.get("answers", [])
    if not answers:
        return False, "填空题答案列表为空"

    if all(not a.strip() for a in answers):
        return False, "填空题所有答案均为空"

    return True, None


def _validate_open_ended(q: dict) -> tuple[bool, Optional[str]]:
    ref = q.get("reference_answer", "") or q.get("correct_answer", "") or ""
    if not ref.strip():
        return False, "开放题缺少参考答案"

    if len(ref.strip()) < 3:
        return False, "参考答案过短"

    return True, None
