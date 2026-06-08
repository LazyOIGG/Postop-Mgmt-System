-- database/migrations/003_guideline_chunks.sql
-- 通用RAG临床指南分块存储
-- 支持任意疾病/手术类型，通过PDF摄入自动填充

CREATE TABLE IF NOT EXISTS guideline_chunks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    surgery_type VARCHAR(100) NOT NULL COMMENT '手术/疾病类型标签（可自由定义，如:膝关节置换术、心脏搭桥术、脑卒中）',
    chunk_index INT NOT NULL COMMENT '分块序号（保持原文档顺序）',
    section_title VARCHAR(300) COMMENT '分块所属章节标题（如：急性期康复训练、术后用药管理）',
    content TEXT NOT NULL COMMENT '分块文本内容（500-2000字）',
    char_count INT DEFAULT 0 COMMENT '字符数',
    source_file VARCHAR(500) COMMENT '来源文件名',
    source_url VARCHAR(500) COMMENT '来源URL（可选）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_surgery (surgery_type),
    INDEX idx_surgery_chunk (surgery_type, chunk_index),
    FULLTEXT INDEX idx_content_ft (content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 将现有 27 条预置指南也转换为通用分块格式
INSERT INTO guideline_chunks (surgery_type, chunk_index, section_title, content, char_count, source_file, source_url)
SELECT
    surgery_type,
    ROW_NUMBER() OVER (PARTITION BY surgery_type ORDER BY phase, category) as chunk_index,
    CONCAT('[', phase, '][', category, '] ', title) as section_title,
    content,
    CHAR_LENGTH(content) as char_count,
    source as source_file,
    '' as source_url
FROM rehab_guidelines
WHERE content IS NOT NULL AND CHAR_LENGTH(content) > 0;

SELECT CONCAT('Migrated ', COUNT(*), ' existing guidelines to chunks') AS result FROM guideline_chunks;
