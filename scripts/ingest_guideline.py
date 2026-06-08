#!/usr/bin/env python
"""
通用临床指南PDF摄入工具

用法:
    python scripts/ingest_guideline.py \\
        --pdf ./guidelines/TKA_rehab_AAOS.pdf \\
        --type "膝关节置换术" \\
        [--url "https://orthoinfo.aaos.org/..."]

功能:
    1. PyMuPDF 提取PDF全部文本
    2. 按章节标题智能分块（识别中文/英文/数字标题模式）
    3. 每块500-2000字
    4. 存入 guideline_chunks 表
    5. 支持重复摄入（先删该疾病旧数据再导入，幂等）

支持的章节分块识别模式：
    - 中文编号: 一、二、三、... / 1. 2. 3. / (一)(二)(三) / 第X章 第X节
    - 阶段标题: 急性期 / 恢复期 / 巩固期 / Phase 1 / Phase I / Week 1-2
    - 类别标题: 运动 / 用药 / 饮食 / 复查 / 注意事项 / Exercise / Medication
"""
import argparse
import re
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # PyMuPDF


# ── 章节分块标题检测模式 ──────────────────────────────────────────
SECTION_PATTERNS = [
    # 中文编号标题
    re.compile(r'^[一二三四五六七八九十]+[、，．.]\s*.+'),        # 一、术后康复原则
    re.compile(r'^（[一二三四五六七八九十]+）\s*.+'),            # （一）早期活动
    re.compile(r'^第[一二三四五六七八九十\d]+[章节部分段]\s*.+'), # 第一章 / 第3节
    re.compile(r'^\d+[\.\、\s)]{1,2}\s*[^\d].+'),               # 1. 概述 / 1) 运动训练
    # 阶段标识
    re.compile(r'(急性期|恢复期|巩固期|术前|术后|围手术期|出院后).*[:：].*'),
    re.compile(r'(Phase|Stage|Week)\s*[IVX\d]+.*[:：].*', re.IGNORECASE),
    re.compile(r'(第\s*\d+\s*[周天月]).*[:：].*'),              # 第1周：...
    # 类别标识
    re.compile(r'(运动|锻炼|用药|药物|饮食|营养|复查|随访|注意事项|禁忌|安全).*[:：].*'),
    re.compile(r'(Exercise|Medication|Diet|Review|Precaution|Contraindication).*[:：].*', re.IGNORECASE),
    # 任何粗体/大写开头的短行（可能是英文标题）
    re.compile(r'^[A-Z][A-Za-z\s]{3,60}$'),
]

MIN_CHUNK_CHARS = 300   # 分块最小字符数（小于此值的合并到上一块）
MAX_CHUNK_CHARS = 2500  # 分块最大字符数（超过此值的尝试在段落边界拆分）
TARGET_CHUNK_CHARS = 1200  # 目标分块大小


def extract_text_from_pdf(pdf_path: str) -> str:
    """使用 PyMuPDF 提取 PDF 全部文本"""
    doc = fitz.open(pdf_path)
    full_text = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        if text.strip():
            full_text.append(f"\n--- Page {page_num} ---\n{text}")
    doc.close()
    return "\n".join(full_text)


def is_section_header(line: str) -> bool:
    """判断一行是否为章节标题"""
    line = line.strip()
    if not line or len(line) > 80:  # 标题通常不超过80字
        return False
    for pattern in SECTION_PATTERNS:
        if pattern.match(line):
            return True
    return False


def smart_chunk(text: str) -> list[dict]:
    """智能分块：按章节标题切分，确保每块大小合理"""
    lines = text.split("\n")
    chunks = []
    current_title = "正文"
    current_text = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 跳过页码标记
        if re.match(r'^--- Page \d+ ---$', stripped):
            continue

        # 检测章节标题
        if is_section_header(stripped):
            # 保存前一个块
            if current_text:
                chunk_content = "\n".join(current_text).strip()
                if len(chunk_content) >= MIN_CHUNK_CHARS:
                    chunks.append({
                        "section_title": current_title,
                        "content": chunk_content,
                        "char_count": len(chunk_content)
                    })
                current_text = []
            current_title = stripped[:300]  # 截断过长标题
            continue

        current_text.append(stripped)

    # 保存最后一个块
    if current_text:
        chunk_content = "\n".join(current_text).strip()
        if len(chunk_content) >= MIN_CHUNK_CHARS:
            chunks.append({
                "section_title": current_title,
                "content": chunk_content,
                "char_count": len(chunk_content)
            })

    # 后处理：合并过小的块，拆分过大的块
    merged = _merge_small_chunks(chunks)
    split = _split_large_chunks(merged)
    return split


def _merge_small_chunks(chunks: list[dict]) -> list[dict]:
    """合并字符数过少的分块"""
    if not chunks:
        return chunks
    result = []
    buffer = chunks[0].copy()

    for chunk in chunks[1:]:
        if buffer["char_count"] < MIN_CHUNK_CHARS:
            # 合并到当前 buffer
            buffer["content"] += "\n\n" + chunk["content"]
            buffer["char_count"] += chunk["char_count"]
            # 保留第一个章节标题
        else:
            result.append(buffer)
            buffer = chunk.copy()

    result.append(buffer)
    return result


def _split_large_chunks(chunks: list[dict]) -> list[dict]:
    """在段落边界上拆分过大的分块"""
    result = []
    for chunk in chunks:
        if chunk["char_count"] <= MAX_CHUNK_CHARS:
            result.append(chunk)
            continue

        # 尝试按双换行（段落边界）拆分
        paragraphs = chunk["content"].split("\n\n")
        sub_chunks = []
        current_text = []
        current_len = 0
        sub_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) > TARGET_CHUNK_CHARS and current_text:
                sub_chunks.append({
                    "section_title": f"{chunk['section_title']} (续{sub_idx + 1})" if sub_idx > 0 else chunk["section_title"],
                    "content": "\n\n".join(current_text),
                    "char_count": current_len
                })
                current_text = [para]
                current_len = len(para)
                sub_idx += 1
            else:
                current_text.append(para)
                current_len += len(para)

        if current_text:
            sub_chunks.append({
                "section_title": f"{chunk['section_title']} (续{sub_idx + 1})" if sub_idx > 0 else chunk["section_title"],
                "content": "\n\n".join(current_text),
                "char_count": current_len
            })

        result.extend(sub_chunks)

    return result


def save_chunks_to_db(surgery_type: str, chunks: list[dict],
                      source_file: str = "", source_url: str = ""):
    """将分块存入 MySQL guideline_chunks 表"""
    from database.local_db_utils import db_instance

    if not db_instance._ensure_connection():
        print("ERROR: 无法连接数据库")
        return 0

    # 先删除该疾病类型的旧数据（幂等）
    cursor = db_instance.connection.cursor()
    cursor.execute("DELETE FROM guideline_chunks WHERE surgery_type = %s", (surgery_type,))
    deleted = cursor.rowcount
    db_instance.connection.commit()
    cursor.close()

    # 插入新分块
    inserted = 0
    for i, chunk in enumerate(chunks):
        try:
            cursor = db_instance.connection.cursor()
            cursor.execute("""
                INSERT INTO guideline_chunks
                (surgery_type, chunk_index, section_title, content, char_count, source_file, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                surgery_type,
                i + 1,
                chunk["section_title"],
                chunk["content"],
                chunk["char_count"],
                source_file,
                source_url
            ))
            db_instance.connection.commit()
            cursor.close()
            inserted += 1
        except Exception as e:
            print(f"  WARN: 分块 {i+1} 插入失败: {e}")

    return inserted


def main():
    parser = argparse.ArgumentParser(description="通用临床指南PDF摄入工具")
    parser.add_argument("--pdf", required=True, help="PDF文件路径")
    parser.add_argument("--type", required=True, help="手术/疾病类型标签（如: 膝关节置换术）")
    parser.add_argument("--url", default="", help="来源URL（可选）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览分块结果，不写入数据库")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: 文件不存在: {pdf_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"摄入指南PDF: {pdf_path.name}")
    print(f"疾病标签: {args.type}")
    print(f"{'='*60}\n")

    # Step 1: 提取文本
    print("[1/4] 正在提取PDF文本...")
    text = extract_text_from_pdf(str(pdf_path))
    print(f"  ✓ 提取完成: {len(text)} 字符, {len(text.split(chr(10)))} 行")

    # Step 2: 智能分块
    print("[2/4] 正在智能分块...")
    chunks = smart_chunk(text)
    print(f"  ✓ 分块完成: {len(chunks)} 个分块")
    for i, chunk in enumerate(chunks):
        print(f"    [{i+1}] {chunk['section_title'][:60]}... ({chunk['char_count']}字)")

    # Step 3: 存入数据库
    if args.dry_run:
        print("\n[3/4] DRY RUN — 跳过数据库写入")
    else:
        print(f"\n[3/4] 正在存入数据库 (surgery_type={args.type})...")
        source_name = pdf_path.name
        count = save_chunks_to_db(args.type, chunks, source_name, args.url)
        print(f"  ✓ 已存入 {count} 个分块")

    # Step 4: 完成
    total_chars = sum(c["char_count"] for c in chunks)
    print(f"\n[4/4] 完成!")
    print(f"  疾病: {args.type}")
    print(f"  分块数: {len(chunks)}")
    print(f"  总字符: {total_chars}")
    print(f"  来源: {pdf_path.name}")
    print(f"\n现在可以通过系统生成 {args.type} 的个性化康复计划了!")


if __name__ == "__main__":
    main()
