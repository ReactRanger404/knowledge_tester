"""索引知识库 — 将 kb/ 下的文档切块、向量化、存入向量库。

用法：
  python scripts/index_kb.py             索引所有新文档
  python scripts/index_kb.py --force     重新索引全部
  python scripts/index_kb.py --search "列表"  搜索测试
"""
import sys, os, asyncio, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from rag.vector_store import get_store, index_all_kb

async def main():
    parser = argparse.ArgumentParser(description="索引知识库到向量库")
    parser.add_argument("--force", action="store_true", help="强制重新索引全部")
    parser.add_argument("--search", type=str, default="", help="搜索测试")
    args = parser.parse_args()

    store = get_store()

    if args.search:
        print(f"\n[搜索] {args.search}\n")
        results = await store.search(args.search, top_k=5)
        for r in results:
            print(f"  [{r['score']:.3f}] {r['doc_name']}")
            print(f"  {r['text'][:200]}...\n")
        return

    if args.force:
        kb_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb")
        for name in os.listdir(kb_dir):
            if os.path.isdir(os.path.join(kb_dir, name)):
                store.remove_document(name)
        print("- 已清除所有索引")

    print("[知识库] 索引中...")
    results = await index_all_kb()
    if results:
        for r in results:
            print(f"  + {r['name']}: {r['chunks']} 个文本块")
    else:
        print("  没有新文档需要索引")

    docs = store.get_documents()
    print(f"\n已索引的文档: {docs}")

if __name__ == "__main__":
    asyncio.run(main())
