"""工具定义 — 每个题型一个文件。"""

from .choice import TOOL_CHOICE
from .judgment import TOOL_JUDGMENT
from .fill_blank import TOOL_FILL_BLANK
from .short_answer import TOOL_SHORT_ANSWER
from .essay import TOOL_ESSAY

# TA 用的工具查找表
TA_TOOLS = {
    "choice": TOOL_CHOICE,
    "judgment": TOOL_JUDGMENT,
    "fill_blank": TOOL_FILL_BLANK,
    "short_answer": TOOL_SHORT_ANSWER,
    "essay": TOOL_ESSAY,
}
