"""导入 PDF 到知识库。

用法：
  python scripts/import_pdf.py "C:/path/to/教材.pdf" [--name "教材名称"]
  python scripts/import_pdf.py "C:/path/to/教材.pdf" --name "Python基础" --max-chars 100000
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def extract_pdf_text(pdf_path: str, max_chars: int = 500000) -> tuple[str, int]:
    """提取 PDF 文本，返回 (文本内容, 总页数)。500000 字符约 300 页。"""
    import fitz
    doc = fitz.open(pdf_path)
    total = len(doc)
    parts, count = [], 0
    for i, page in enumerate(doc):
        t = page.get_text()
        if count + len(t) > max_chars:
            parts.append(f"\n\n[已截断，仅前 {i}/{total} 页]")
            break
        parts.append(t)
        count += len(t)
    doc.close()
    return "".join(parts), total

def main():
    parser = argparse.ArgumentParser(description="导入 PDF 到知识库")
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--name", "-n", default="", help="教材名称（默认用文件名）")
    parser.add_argument("--max-chars", "-m", type=int, default=100000, help="最大提取字符数")
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"❌ 文件不存在: {args.pdf}")
        return

    name = args.name or os.path.splitext(os.path.basename(args.pdf))[0]
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb", name)
    os.makedirs(kb_dir, exist_ok=True)

    print(f"📖 正在提取: {name}")
    text, pages = extract_pdf_text(args.pdf, args.max_chars)
    char_count = len(text)
    print(f"   共 {pages} 页，提取 {char_count} 字符")

    # 保存内容
    with open(os.path.join(kb_dir, "content.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    # 保存元数据
    meta = {"name": name, "source": args.pdf, "pages": pages, "char_count": char_count}
    with open(os.path.join(kb_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✅ 已导入到 kb/{name}/")
    print(f"   内容: kb/{name}/content.txt ({char_count} 字符)")
    print(f"   元数据: kb/{name}/meta.json")

if __name__ == "__main__":
    main()
