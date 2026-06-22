"""RAG 向量存储 — 启动时自动索引 kb/，出题时语义检索。

流程：
  启动 → 扫描 kb/ 新文件 → 提取文字 → 切块 → embedding → ChromaDB
  出题 → 语义检索相关块 → 拼成 source_material → 知识点提取
"""
import os, json, re, hashlib
from typing import Optional

# ChromaDB 存储路径
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")
KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb")

CHUNK_SIZE = 800   # 每块字符数
OVERLAP = 100      # 重叠
MAX_CHUNKS = 60    # 出题最多检索 60 块


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
    """基于 ChromaDB 的向量存储，启动时自动增量索引。"""

    def __init__(self):
        self._collection = None
        self._initialized = False

    async def _ensure_init(self):
        if self._initialized: return
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        try:
            self._collection = client.get_collection("kb")
        except Exception:
            self._collection = client.create_collection("kb")
        self._initialized = True

    def _doc_id(self, doc_name: str) -> str:
        return hashlib.md5(doc_name.encode()).hexdigest()[:12]

    async def add_document(self, doc_name: str, text: str) -> int:
        """将文档切块、向量化、存入 ChromaDB。"""
        await self._ensure_init()
        # 删除旧数据
        doc_id = self._doc_id(doc_name)
        try:
            self._collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

        chunks = chunk_text(text)
        ids = []
        metadatas = []
        documents = []
        for i, chunk in enumerate(chunks):
            cid = f"{doc_id}_{i}"
            ids.append(cid)
            documents.append(chunk["text"])
            metadatas.append({
                "doc_id": doc_id,
                "doc_name": doc_name,
                "chapter": chunk.get("chapter", ""),
                "chunk_index": i,
            })

        if ids:
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    async def search(self, query: str, top_k: int = MAX_CHUNKS, doc_name: str = "") -> list[dict]:
        """语义检索最相关的文本块。"""
        await self._ensure_init()
        where = {"doc_name": doc_name} if doc_name else None
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
            )
        except Exception as e:
            print(f"[RAG] 检索失败: {e}")
            return []

        items = []
        if results and results["ids"]:
            for i, cid in enumerate(results["ids"][0]):
                items.append({
                    "id": cid,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "score": results["distances"][0][i] if results["distances"] else 0,
                    "chapter": results["metadatas"][0][i].get("chapter", "") if results["metadatas"] else "",
                    "doc_name": results["metadatas"][0][i].get("doc_name", "") if results["metadatas"] else "",
                })
        return items

    async def get_text_for_exam(self, doc_name: str) -> str:
        """语义检索出题用文本：以文档名作为查询，获取最相关块。"""
        # 用文档名作为检索查询
        results = await self.search(doc_name, top_k=MAX_CHUNKS)
        if not results:
            return ""

        # 按 chunk_index 排序还原顺序
        def _sort_key(r):
            try: return int(r["id"].rsplit("_", 1)[-1])
            except: return 0
        results.sort(key=_sort_key)

        texts = [r["text"] for r in results]
        text = "\n".join(texts)

        total = await self.get_chunk_count(doc_name)
        if total > MAX_CHUNKS:
            text += f"\n\n[全文共 {total} 块，已检索前 {len(results)} 块]"
        return text

    async def get_documents(self) -> list[dict]:
        """返回所有已索引的文档信息。"""
        await self._ensure_init()
        try:
            data = self._collection.get()
            doc_map = {}
            for i, doc_name in enumerate(data["metadatas"][i]["doc_name"] for i in range(len(data["ids"]))):
                doc_map.setdefault(doc_name, {"chunks": 0, "chapters": set()})
                doc_map[doc_name]["chunks"] += 1
                ch = data["metadatas"][i].get("chapter", "")
                if ch: doc_map[doc_name]["chapters"].add(ch)

            result = []
            for name, info in doc_map.items():
                result.append({"name": name, "chunks": info["chunks"], "chapters": sorted(info["chapters"])})
            return result
        except Exception:
            return []

    async def get_chunk_count(self, doc_name: str) -> int:
        docs = await self.get_documents()
        for d in docs:
            if d["name"] == doc_name: return d["chunks"]
        return 0

    async def get_chapters(self, doc_name: str) -> list[str]:
        docs = await self.get_documents()
        for d in docs:
            if d["name"] == doc_name: return d["chapters"]
        return []


_store: Optional[VectorStore] = None

def get_store() -> VectorStore:
    global _store
    if _store is None: _store = VectorStore()
    return _store


async def auto_index_kb():
    """启动时自动扫描 kb/，增量索引新文件。"""
    store = get_store()
    if not os.path.isdir(KB_DIR): return []

    # 获取已索引的文档名
    indexed = {d["name"] for d in await store.get_documents()}
    results = []
    for name in sorted(os.listdir(KB_DIR)):
        if name in indexed:
            continue
        content_path = os.path.join(KB_DIR, name, "content.txt")
        if os.path.isfile(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                text = f.read()
            count = await store.add_document(name, text)
            results.append({"name": name, "chunks": count})
            print(f"  [RAG] 索引: {name} ({count} 块)")
    return results
