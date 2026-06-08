"""通用RAG临床指南检索服务

检索策略（两级）：
  1. 优先检索 guideline_chunks 表（通过PDF摄入的通用分块数据）
  2. 回退到 rehab_guidelines 表（预置的结构化指南）
  3. 都无结果则返回空，LLM依靠自身知识制定计划
"""

from typing import Dict, List, Optional
from app.db.session import db_instance


class RehabGuidelineService:

    # ── 公开接口 ──────────────────────────────────────────────────

    def format_for_prompt(self, surgery_type: str) -> str:
        """检索指南并格式化为 LLM prompt 片段

        返回空字符串表示无匹配指南（LLM将使用自身知识）
        """
        # 优先级1: chunk表（通用，支持任意疾病）
        chunks = self._get_chunks(surgery_type)
        if chunks:
            return self._format_chunks_for_prompt(chunks, surgery_type)

        # 优先级2: 结构化指南表（预置的3种手术）
        return self._format_structured_for_prompt(surgery_type)

    def get_stats(self, surgery_type: str = None) -> Dict:
        """获取指南库统计信息"""
        stats = {"chunked": 0, "structured": 0, "surgeries": []}
        try:
            if not db_instance._ensure_connection():
                return stats
            cursor = db_instance.connection.cursor(dictionary=True)

            # chunk表统计
            cursor.execute(
                "SELECT COUNT(*) as cnt, COUNT(DISTINCT surgery_type) as types FROM guideline_chunks"
            )
            row = cursor.fetchone()
            if row:
                stats["chunked"] = row["cnt"]
                stats["structured_types_count"] = row["types"]

            # 获取所有疾病类型
            cursor.execute(
                "SELECT DISTINCT surgery_type, COUNT(*) as cnt FROM guideline_chunks GROUP BY surgery_type ORDER BY cnt DESC"
            )
            stats["surgeries"] = cursor.fetchall()

            # 结构化指南统计
            cursor.execute("SELECT COUNT(*) as cnt FROM rehab_guidelines")
            row = cursor.fetchone()
            if row:
                stats["structured"] = row["cnt"]

            cursor.close()
        except Exception as e:
            print(f"获取指南统计失败: {e}")
        return stats

    # ── 分块检索（通用，支持任意疾病） ────────────────────────────

    def _get_chunks(self, surgery_type: str, max_chunks: int = 15) -> List[Dict]:
        """从 guideline_chunks 表检索分块

        策略：精确匹配 surgery_type → 按 chunk_index 排序 → 返回top-K
        限制总字符数约12000字以保证prompt不超长
        """
        try:
            if not db_instance._ensure_connection():
                return []
            cursor = db_instance.connection.cursor(dictionary=True)

            # 精确匹配 + 通用指南
            query = """
                SELECT id, surgery_type, chunk_index, section_title,
                       content, char_count, source_file, source_url
                FROM guideline_chunks
                WHERE surgery_type IN (%s, '通用')
                ORDER BY FIELD(surgery_type, %s, '通用'), chunk_index
                LIMIT %s
            """
            cursor.execute(query, (surgery_type, surgery_type, max_chunks))
            chunks = cursor.fetchall()
            cursor.close()

            # 控制总字符数
            total_chars = 0
            selected = []
            for chunk in chunks:
                if total_chars + chunk["char_count"] > 15000:
                    break
                selected.append(chunk)
                total_chars += chunk["char_count"]

            return selected
        except Exception as e:
            print(f"检索分块指南失败: {e}")
            return []

    def _format_chunks_for_prompt(self, chunks: List[Dict], surgery_type: str) -> str:
        """将分块格式化为 LLM prompt"""
        if not chunks:
            return ""

        lines = [
            "## 📚 循证临床指南（RAG检索自权威医学文献）",
            f"以下内容来自 {surgery_type} 的专业临床指南文档，你必须严格依据以下内容制定康复方案。",
            ""
        ]

        current_section = None
        for chunk in chunks:
            section = chunk.get("section_title", "")
            # 如果章节变了，加一个分隔
            if section != current_section:
                lines.append(f"\n### {section}")
                current_section = section

            lines.append(chunk["content"])

            # 来源标注
            source = chunk.get("source_file") or chunk.get("source_url") or ""
            if source:
                lines.append(f"> 📖 来源: {source}")

        return "\n".join(lines)

    # ── 结构化指南检索（旧表，预置的3种手术） ─────────────────────

    def _format_structured_for_prompt(self, surgery_type: str) -> str:
        """从旧 rehab_guidelines 表检索（回退方案）"""
        phases = ["急性期", "恢复期", "巩固期"]
        all_guidelines = []
        seen_ids = set()

        for phase in phases:
            guidelines = db_instance.get_rehab_guidelines(surgery_type, phase)
            for g in guidelines:
                if g["id"] not in seen_ids:
                    all_guidelines.append(g)
                    seen_ids.add(g["id"])

        general = db_instance.get_rehab_guidelines("通用", None)
        for g in general:
            if g["id"] not in seen_ids:
                all_guidelines.append(g)
                seen_ids.add(g["id"])

        if not all_guidelines:
            return ""

        lines = ["## 📚 循证临床指南（预置知识库）"]

        for phase in phases:
            phase_guidelines = [g for g in all_guidelines
                              if g.get("phase") == phase or g.get("phase") == "通用"]
            if not phase_guidelines:
                continue
            lines.append(f"\n### {phase}")
            for g in phase_guidelines:
                lines.append(f"【{g.get('category','')}】{g.get('title','')}：{g.get('content','')}")
                if g.get("source"):
                    lines.append(f"  → 来源: {g['source']}（{g.get('evidence_level','专家共识')}）")

        return "\n".join(lines) if len(lines) > 1 else ""


rehab_guideline_service = RehabGuidelineService()
