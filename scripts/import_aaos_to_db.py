# -*- coding: utf-8 -*-
"""
将 AAOS 爬虫产出的 JSON 文件导入到 guideline_chunks 表
每个运动 = 一个 chunk，含文字 + 图片URL
"""

import json, sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.session import db_instance

TEXT_DIR = Path("D:/study/大三/26春 软件工程创新实践/网页源码/text_output")
IMAGE_DIR = Path("D:/study/大三/26春 软件工程创新实践/网页源码/images")

# 中文标签 → surgery_type 映射
LABEL_MAP = {
    "膝关节锻炼": "膝关节锻炼",
    "髋关节锻炼": "髋关节锻炼",
    "肩关节锻炼": "肩关节锻炼",
    "脊柱锻炼": "脊柱锻炼",
    "足踝锻炼": "足踝锻炼",
    "肘关节锻炼": "肘关节锻炼",
    "全膝关节置换术": "全膝关节置换术",
    "全髋关节置换术": "全髋关节置换术",
    "全肩关节置换术": "全肩关节置换术",
    "全膝关节置换术后活动": "全膝关节置换术",
    "全髋关节置换术后活动": "全髋关节置换术",
    "全肩关节置换术后活动": "全肩关节置换术",
    "ACL重建术": "ACL重建术",
    "半月板修复术": "半月板修复术",
    "膝关节镜手术": "膝关节镜手术",
    "肩袖修复术": "肩袖修复术",
    "肩关节镜手术": "肩关节镜手术",
    "肩关节不稳术后": "肩关节不稳术后",
    "肩关节术后锻炼": "肩关节术后锻炼",
    "锁骨骨折": "锁骨骨折",
    "踝关节骨折": "踝关节骨折",
    "跟腱修复术": "跟腱修复术",
    "踝关节扭伤": "踝关节扭伤",
    "足底筋膜炎": "足底筋膜炎",
    "拇囊炎术后": "拇囊炎术后",
    "腕管松解术": "腕管松解术",
    "网球肘": "网球肘",
    "手腕骨折": "手腕骨折",
    "肘关节骨折": "肘关节骨折",
    "肱骨骨折": "肱骨骨折",
    "腰椎管狭窄": "腰椎管狭窄",
    "颈椎管狭窄": "颈椎管狭窄",
    "腰椎融合术后": "腰椎融合术后",
    "椎间盘切除术后": "腰椎间盘手术",
    "腰椎术后锻炼": "腰椎间盘手术",
    "股骨颈骨折": "股骨颈骨折",
    "髋关节镜手术": "髋关节镜手术",
    "脊柱融合术后活动": "脊柱融合术后",
}


def import_all():
    if not db_instance._ensure_connection():
        print("ERROR: 无法连接数据库")
        return

    # 清空AAOS导入的旧数据（保留手动录入的 rehab_guidelines 表数据）
    cursor = db_instance.connection.cursor()
    cursor.execute("DELETE FROM guideline_chunks WHERE source_file LIKE '%orthoinfo%'")
    deleted = cursor.rowcount
    db_instance.connection.commit()
    cursor.close()
    print(f"已清空 {deleted} 条旧AAOS数据")

    json_files = sorted(TEXT_DIR.glob("*.json"))
    total_exercises = 0

    for jf in json_files:
        label = jf.stem  # 文件名（含中文标签）
        if label == "测试":
            continue

        surgery_type = LABEL_MAP.get(label, label)
        data = json.loads(jf.read_text(encoding="utf-8"))

        items = data.get("items", [])
        exercise_count = 0

        for item_idx, item in enumerate(items):
            name = item.get("name", "").strip()
            if not name or "Getting Started" in name or "Warm" in name:
                continue

            content_parts = []
            if item.get("muscles"):
                content_parts.append(f"目标肌肉：{item['muscles']}")
            if item.get("equipment"):
                content_parts.append(f"器材：{item['equipment']}")
            if item.get("repetitions"):
                content_parts.append(f"频率：{item['repetitions']}")
            if item.get("steps"):
                content_parts.append("步骤：\n" + "\n".join(f"- {s}" for s in item["steps"]))
            for tip in item.get("tips", []):
                content_parts.append(f"提示：{tip}")

            content = "\n\n".join(content_parts)
            if not content.strip():
                continue

            # 图片URL
            image_urls = item.get("image_urls", [])

            exercise_count += 1
            total_exercises += 1

            # chunk_index 使用 item_idx+1（与图片文件名后缀一致）
            chunk_idx = item_idx + 1

            # 存入 guideline_chunks
            try:
                cursor = db_instance.connection.cursor()
                cursor.execute("""
                    INSERT INTO guideline_chunks
                    (surgery_type, chunk_index, section_title, content, char_count, source_file, source_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    surgery_type,
                    chunk_idx,
                    name,
                    content + ("\n\n图片：" + ", ".join(image_urls) if image_urls else ""),
                    len(content),
                    data.get("url", ""),
                    json.dumps(image_urls, ensure_ascii=False) if image_urls else "",
                ))
                db_instance.connection.commit()
                cursor.close()
            except Exception as e:
                print(f"  WARN: {surgery_type}/{name}: {e}")

        print(f"  {label}: {exercise_count} exercises")

    print(f"\nTotal: {total_exercises} exercises imported")
    print(f"Surgery types: {len(set(LABEL_MAP.values()))}")


if __name__ == "__main__":
    import_all()
