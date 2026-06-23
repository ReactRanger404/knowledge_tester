"""RAG 向量存储 — pgvector 版。

启动自动索引 kb/ → 切块 → embedding → 存 pgvector。
"""
import os, re, hashlib, json, asyncio, base64, io
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb")
CHUNK_SIZE = 800
OVERLAP = 100
MAX_CHUNKS = 60
EMBED_DIM = 1024  # DeepSeek embedding 维度

# PostgreSQL 连接参数
PG_CONFIG = {
    "host": os.getenv("PG_HOST", "127.0.0.1"),
    "port": int(os.getenv("PG_PORT", "5433")),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", ""),
    "database": os.getenv("PG_DATABASE", "knowledge_tester"),
}


def clean_text(text: str) -> str:
    """数据清洗：去除噪声，保留结构（表格、列表、代码块不动）。"""
    # 1. 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. 去除页眉页脚
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        if re.match(r'^\d{1,4}$', s):                # 纯数字页码
            continue
        if re.match(r'^[—\-]\s*\d+\s*[—\-]$', s):    # — X — 页码
            continue
        if re.match(r'^第[\d一二三四五六七八九十]+页$', s):  # 第X页
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)

    # 3. 合并连续空行成单个空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. 行首行尾多余空白
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)

    # 5. 全角英数字 → 半角（保留中文标点语境）
    #    注意：不转中文句号、逗号等，避免破坏结构
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("；", ";").replace("：", ":")
    text = text.replace("？", "?").replace("！", "!")

    # 6. 去除重复空格
    text = re.sub(r' {2,}', ' ', text)

    # 7. 去除零宽字符
    text = re.sub(r'[​‌‍﻿]', '', text)

    return text.strip()


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=OVERLAP) -> list[dict]:
    """切块 + 自动标注章节。"""
    chunks = []
    chapter_map = {}
    for m in re.finditer(r'(第[一二三四五六七八九十零\d]+[章节部篇][ \t]*[^\n]*)', text[:5000]):
        chapter_map[m.start()] = m.group().strip()
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chapter = "开头"
        for pos in sorted(chapter_map.keys()):
            if pos <= start: chapter = chapter_map[pos]
            else: break
        chunks.append({"text": text[start:end], "chapter": chapter})
        start += chunk_size - overlap
    return chunks


class VectorStore:
    """pgvector 向量存储。"""

    def __init__(self):
        self._pool = None
        self._initialized = False

    async def _ensure_init(self):
        if self._initialized: return
        import asyncpg
        self._pool = await asyncpg.create_pool(**PG_CONFIG, min_size=1, max_size=5)
        # 建表（幂等）
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS kb_chunks (
                    id TEXT PRIMARY KEY,
                    doc_name TEXT NOT NULL,
                    chapter TEXT DEFAULT '',
                    chunk_index INT DEFAULT 0,
                    content TEXT NOT NULL,
                    embedding vector(1024)
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_doc_name ON kb_chunks(doc_name)")
        self._initialized = True

    async def _embed(self, text: str) -> list[float]:
        """基于文本哈希的确定性向量（零外部依赖）。"""
        import hashlib, numpy as np
        # 用 MD5 哈希生成 1024 维确定性向量
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:8], 'big') % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(EMBED_DIM).astype(np.float32)
        vec = vec / (np.linalg.norm(vec) + 1e-10)  # 归一化
        return vec.tolist()

    async def add_document(self, doc_name: str, text: str) -> int:
        await self._ensure_init()
        doc_id = hashlib.md5(doc_name.encode()).hexdigest()[:12]
        chunks = chunk_text(text)

        # 删除旧数据
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM kb_chunks WHERE doc_name = $1", doc_name)

            for i, chunk in enumerate(chunks):
                cid = f"{doc_id}_{i}"
                emb = await self._embed(chunk["text"])
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                await conn.execute(
                    "INSERT INTO kb_chunks (id, doc_name, chapter, chunk_index, content, embedding) VALUES ($1,$2,$3,$4,$5,$6::vector)",
                    cid, doc_name, chunk["chapter"], i, chunk["text"], emb_str,
                )
        return len(chunks)

    async def search(self, query: str, top_k: int = MAX_CHUNKS, doc_name: str = "") -> list[dict]:
        await self._ensure_init()
        q_emb = await self._embed(query)
        emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"
        if doc_name:
            where = "WHERE doc_name = $2"
            limit = "$3"
            params = [emb_str, doc_name, top_k]
        else:
            where = ""
            limit = "$2"
            params = [emb_str, top_k]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, doc_name, chapter, chunk_index, content, "
                f"1 - (embedding <=> $1::vector) AS score "
                f"FROM kb_chunks {where} "
                f"ORDER BY embedding <=> $1::vector LIMIT {limit}",
                *params,
            )
            return [
                {"id": r["id"], "text": r["content"], "score": round(r["score"], 4),
                 "chapter": r["chapter"], "doc_name": r["doc_name"], "chunk_index": r["chunk_index"]}
                for r in rows
            ]

    async def get_text_for_exam(self, doc_name: str) -> str:
        results = await self.search(doc_name, top_k=MAX_CHUNKS)
        if not results: return ""
        results.sort(key=lambda r: r["chunk_index"])
        text = "\n".join(r["text"] for r in results)
        total = await self.get_chunk_count(doc_name)
        if total > MAX_CHUNKS:
            text += f"\n\n[全文共 {total} 块，已检索前 {len(results)} 块]"
        return text

    async def get_full_text(self, doc_name: str) -> str:
        """获取某个文档的全部文本（按原始顺序拼接）。"""
        await self._ensure_init()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT content FROM kb_chunks WHERE doc_name=$1 ORDER BY chunk_index",
                doc_name,
            )
            return "\n".join(r["content"] for r in rows)

    async def get_documents(self) -> list[dict]:
        await self._ensure_init()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT doc_name, COUNT(*) AS chunks, "
                "ARRAY_AGG(DISTINCT chapter) FILTER (WHERE chapter != '') AS chapters "
                "FROM kb_chunks GROUP BY doc_name ORDER BY doc_name"
            )
            return [
                {"name": r["doc_name"], "chunks": r["chunks"],
                 "chapters": list(r["chapters"]) if r["chapters"] else []}
                for r in rows
            ]

    async def get_chunk_count(self, doc_name: str) -> int:
        await self._ensure_init()
        async with self._pool.acquire() as conn:
            r = await conn.fetchval("SELECT COUNT(*) FROM kb_chunks WHERE doc_name=$1", doc_name)
            return r or 0

    async def get_chapters(self, doc_name: str) -> list[str]:
        await self._ensure_init()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT chapter FROM kb_chunks WHERE doc_name=$1 AND chapter!='' ORDER BY chapter",
                doc_name,
            )
            return [r["chapter"] for r in rows]

    async def get_char_count(self, doc_name: str) -> int:
        """获取某个文档的总字符数（Python len 避免编码问题）。"""
        await self._ensure_init()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT content FROM kb_chunks WHERE doc_name=$1",
                doc_name,
            )
            return sum(len(r["content"]) for r in rows)


_store: Optional[VectorStore] = None

def get_store() -> VectorStore:
    global _store
    if _store is None: _store = VectorStore()
    return _store


def _log(msg: str):
    print(f"  [RAG] {msg}", flush=True)


def _describe_page_image(pix) -> str:
    """将页面截图发给 Vision 模型，返回图表/表格的文字描述（429 无限重试）。"""
    img_bytes = pix.tobytes("png")
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    client = OpenAI(
        api_key=os.getenv("VISION_API_KEY", os.getenv("LLM_API_KEY", "")),
        base_url=os.getenv("VISION_BASE_URL", os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")),
    )
    model = os.getenv("VISION_MODEL", os.getenv("LLM_MODEL", "deepseek-v4-flash"))

    import time
    wait = 1
    while True:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这是教材中的一页，请用中文详细描述其中的技术图表、表格、流程图等内容。如果没有明显图表，回复「无图表」。保持简洁，50字以内。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }],
                max_tokens=200,
                temperature=0.1,
            )
            desc = resp.choices[0].message.content or ""
            desc = desc.strip().replace("无图表", "").strip()
            return desc
        except Exception as e:
            if "429" in str(e):
                _log(f"  限流，{wait}秒后重试...")
                time.sleep(wait)
                wait = min(wait * 2, 16)  # 指数退避，上限16秒
            else:
                raise e


def extract_pdf_text(pdf_path: str, max_chars: int = 500000) -> str:
    """提取 PDF 文字。先试 PyMuPDF（文字版），不够再走 OCR（含 Vision 图表描述）。"""
    import fitz
    doc = fitz.open(pdf_path)
    total = len(doc)

    # 先试 PyMuPDF 直接提取
    parts, count = [], 0
    for i, page in enumerate(doc):
        t = page.get_text()
        if count + len(t) > max_chars: break
        parts.append(t)
        count += len(t)
    doc.close()

    text = "".join(parts)

    # 如果提取到的文字太少 → 扫描版，走 OCR + Vision
    if len(text) < 100 and total > 5:
        _log(f"文字提取仅 {len(text)} 字符，判定为扫描版 PDF，启动 OCR...")
        import numpy as np
        try:
            import easyocr
            reader = easyocr.Reader(['ch_sim', 'en'], gpu=True, verbose=False)
            ocr_parts, ocr_count = [], 0
            pdf_doc = fitz.open(pdf_path)
            max_pages = len(pdf_doc)

            for i in range(max_pages):
                page = pdf_doc[i]
                # ── OCR 文字 ──
                pix = page.get_pixmap(dpi=150)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if pix.n == 4: img = img[:,:,:3]
                result = reader.readtext(img, detail=1)
                page_text = ""
                if result:
                    page_text = "\n".join([item[1] for item in result])

                # ── Vision 图表描述 ──
                # 只有 OCR 文字中包含"图X-X"、"表X-X"等标记才调用，省 API
                if re.search(r'[图表]\s*\d[\s\-—,.]*\d', page_text):
                    try:
                        desc = _describe_page_image(pix)
                        if desc:
                            page_text += f"\n\n[图表描述] {desc}"
                        import time
                        time.sleep(0.5)  # 限流保护
                    except Exception as ve:
                        _log(f"  第{i+1}页 Vision 描述失败: {ve}")

                if page_text:
                    if ocr_count + len(page_text) > max_chars: break
                    ocr_parts.append(page_text)
                    ocr_count += len(page_text)
                if i % 5 == 0:
                    _log(f"OCR 进度: {i+1}/{max_pages} 页 ({ocr_count} 字符)")

            pdf_doc.close()
            text = "\n".join(ocr_parts)
            _log(f"OCR+Vision 完成: {len(text)} 字符")
        except Exception as e:
            _log(f"OCR 失败: {e}，使用原始提取结果 ({len(text)} 字符)")

    return text


async def auto_index_kb():
    """启动时自动增量索引 kb/ 下的新文档（支持 PDF / content.txt）。"""
    store = get_store()
    if not os.path.isdir(KB_DIR): return []
    indexed = {d["name"] for d in await store.get_documents()}
    results = []

    for item in sorted(os.listdir(KB_DIR)):
        item_path = os.path.join(KB_DIR, item)

        if os.path.isdir(item_path):
            name = item
            if name in indexed:
                _log(f"跳过（已索引）: {name}")
                continue
            content_path = os.path.join(item_path, "content.txt")
            pdf_files = [f for f in os.listdir(item_path) if f.lower().endswith(".pdf")]

            text = ""
            if os.path.isfile(content_path):
                with open(content_path, "r", encoding="utf-8") as f:
                    text = f.read()
                _log(f"读取文件: {name} ({len(text)} 字符)")
            elif pdf_files:
                pdf_path = os.path.join(item_path, pdf_files[0])
                _log(f"发现 PDF: {pdf_files[0]}，正在提取文字...")
                try:
                    text = extract_pdf_text(pdf_path)
                    with open(content_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    _log(f"PDF 提取完成: {len(text)} 字符")
                except Exception as e:
                    _log(f"PDF 提取失败: {e}")
                    continue
            else:
                _log(f"跳过: {name}（无 content.txt 也无 PDF）")
                continue

            if len(text) < 10:
                _log(f"跳过: {name}（内容不足）")
                continue
            text = clean_text(text)
            _log(f"正在索引: {name} ({len(text)} 字符)...")
            count = await store.add_document(name, text)
            results.append({"name": name, "chunks": count})
            _log(f"完成: {name} → {count} 个文本块")

        elif item.lower().endswith(".pdf"):
            name = os.path.splitext(item)[0]
            if name in indexed:
                _log(f"跳过（已索引）: {name}")
                continue
            _log(f"发现 PDF: {item}，正在提取文字...")
            try:
                text = extract_pdf_text(item_path)
                if len(text) < 10:
                    _log(f"跳过: {name}（内容不足）")
                    continue
                _log(f"PDF 提取完成: {len(text)} 字符")
                text = clean_text(text)
                _log(f"正在索引: {name} ({len(text)} 字符)...")
                count = await store.add_document(name, text)
                results.append({"name": name, "chunks": count})
                _log(f"完成: {name} → {count} 个文本块")
            except Exception as e:
                _log(f"PDF 提取失败: {e}")

    if results:
        _log(f"索引汇总: {len(results)} 个文档")
        for r in results:
            _log(f"  + {r['name']}: {r['chunks']} 块")
    else:
        _log("没有新文档需要索引")
    return results
