-- database/migrations/001_rehab_upgrade.sql
-- 康复计划模块全面升级 - 数据库迁移

-- 1. rehab_metrics 量化指标表
CREATE TABLE IF NOT EXISTS rehab_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    metric_type ENUM('pain_vas', 'rom_flexion', 'rom_extension', 'muscle_strength',
                     'weight', 'temperature', 'blood_pressure_sys', 'blood_pressure_dia',
                     'heart_rate', 'sleep_hours', 'wound_status', 'swelling_level',
                     'walking_distance', 'custom') NOT NULL,
    metric_value DECIMAL(10,2),
    metric_unit VARCHAR(20),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_metric (plan_id, metric_date, metric_type),
    FOREIGN KEY (plan_id) REFERENCES rehab_plans(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 2. rehab_exercises 运动指导库
CREATE TABLE IF NOT EXISTS rehab_exercises (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    category ENUM('stretching', 'strength', 'balance', 'mobility', 'breathing', 'other') DEFAULT 'other',
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'easy',
    target_body_part VARCHAR(50),
    surgery_type_tag VARCHAR(50),
    video_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    image_urls JSON,
    description TEXT,
    steps JSON,
    duration_minutes INT DEFAULT 5,
    repetitions INT DEFAULT 10,
    precautions TEXT,
    phase_suitable VARCHAR(10) DEFAULT '恢复期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. rehab_journals 康复日志
CREATE TABLE IF NOT EXISTS rehab_journals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    journal_date DATE NOT NULL,
    mood ENUM('great','good','okay','bad','terrible'),
    pain_level TINYINT CHECK(pain_level BETWEEN 0 AND 10),
    content TEXT,
    photo_urls JSON,
    voice_url VARCHAR(500),
    sleep_quality TINYINT CHECK(sleep_quality BETWEEN 1 AND 5),
    appetite TINYINT CHECK(appetite BETWEEN 1 AND 5),
    energy_level TINYINT CHECK(energy_level BETWEEN 1 AND 5),
    questions_for_doctor TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_journal (plan_id, journal_date),
    FOREIGN KEY (plan_id) REFERENCES rehab_plans(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. achievement_defs + user_achievements 成就系统
CREATE TABLE IF NOT EXISTS achievement_defs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    icon_url VARCHAR(500),
    category ENUM('streak','milestone','compliance','recovery','special') DEFAULT 'streak',
    condition_json JSON,
    points INT DEFAULT 10
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_achievements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    plan_id INT NOT NULL,
    achievement_id INT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_achievement (username, plan_id, achievement_id),
    FOREIGN KEY (achievement_id) REFERENCES achievement_defs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 扩展 rehab_plans（使用条件式添加列，支持重复执行）
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='plan_type')=0, 'ALTER TABLE rehab_plans ADD COLUMN plan_type VARCHAR(20) DEFAULT ''ai_generated''', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='target_metrics')=0, 'ALTER TABLE rehab_plans ADD COLUMN target_metrics JSON', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='total_completion_rate')=0, 'ALTER TABLE rehab_plans ADD COLUMN total_completion_rate DECIMAL(5,2) DEFAULT 0', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='current_streak')=0, 'ALTER TABLE rehab_plans ADD COLUMN current_streak INT DEFAULT 0', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='longest_streak')=0, 'ALTER TABLE rehab_plans ADD COLUMN longest_streak INT DEFAULT 0', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='last_checkin_date')=0, 'ALTER TABLE rehab_plans ADD COLUMN last_checkin_date DATE', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='surgery_date')=0, 'ALTER TABLE rehab_plans ADD COLUMN surgery_date DATE', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plans' AND COLUMN_NAME='doctor_feedback')=0, 'ALTER TABLE rehab_plans ADD COLUMN doctor_feedback JSON', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- 6. 扩展 rehab_plan_tasks（使用条件式添加列，支持重复执行）
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plan_tasks' AND COLUMN_NAME='exercise_id')=0, 'ALTER TABLE rehab_plan_tasks ADD COLUMN exercise_id INT', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plan_tasks' AND COLUMN_NAME='completed_at')=0, 'ALTER TABLE rehab_plan_tasks ADD COLUMN completed_at TIMESTAMP NULL', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plan_tasks' AND COLUMN_NAME='patient_note')=0, 'ALTER TABLE rehab_plan_tasks ADD COLUMN patient_note TEXT', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
SET @s = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='rehab_plan_tasks' AND COLUMN_NAME='difficulty_rating')=0, 'ALTER TABLE rehab_plan_tasks ADD COLUMN difficulty_rating TINYINT', 'SELECT 1'); PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- 7. 预置种子数据：成就定义
INSERT IGNORE INTO achievement_defs (code, name, description, category, condition_json, points) VALUES
('streak_7', '一周坚持', '连续7天完成所有康复任务', 'streak', '{"type":"streak","days":7}', 10),
('streak_14', '两周不懈', '连续14天完成所有康复任务', 'streak', '{"type":"streak","days":14}', 20),
('streak_30', '月度之星', '连续30天完成所有康复任务', 'streak', '{"type":"streak","days":30}', 50),
('streak_60', '康复达人', '连续60天完成所有康复任务', 'streak', '{"type":"streak","days":60}', 100),
('first_phase_complete', '初战告捷', '完成急性期所有任务', 'milestone', '{"type":"phase_complete","phase":"急性期"}', 20),
('second_phase_complete', '稳步前进', '完成恢复期所有任务', 'milestone', '{"type":"phase_complete","phase":"恢复期"}', 30),
('all_phases_complete', '康复圆满', '完成全部三个阶段', 'milestone', '{"type":"phase_complete","phase":"巩固期"}', 100),
('full_compliance_7', '完美一周', '连续7天用药准时率100%', 'compliance', '{"type":"compliance","days":7}', 15),
('journal_streak_7', '日志达人', '连续7天写康复日志', 'special', '{"type":"journal_streak","days":7}', 15),
('pain_reduced', '疼痛减轻', 'VAS疼痛评分降至3分以下', 'recovery', '{"type":"metric","target":"pain_vas","operator":"lte","value":3}', 25),
('rom_improved', '活动度突破', '关节屈曲活动度提升超过30度', 'recovery', '{"type":"metric_improvement","target":"rom_flexion","delta":30}', 25),
('first_walk', '首次下床', '完成首次下床行走任务', 'milestone', '{"type":"task_complete","keyword":"下床"}', 15);

-- 8. 预置种子数据：运动指导
INSERT IGNORE INTO rehab_exercises (title, category, difficulty, target_body_part, surgery_type_tag, description, steps, duration_minutes, repetitions, precautions, phase_suitable) VALUES
('踝泵运动', 'mobility', 'easy', '踝关节', '通用', '通过踝关节的屈伸活动促进下肢血液循环，预防深静脉血栓。', '["平躺或坐在床上，双腿伸直","缓慢将脚尖向头部方向勾起，保持5秒","缓慢将脚尖向下方压，保持5秒","重复上述动作"]', 5, 20, '如感小腿疼痛加剧，请暂停并咨询医生', '急性期'),
('股四头肌等长收缩', 'strength', 'easy', '膝关节', '膝关节置换术', '不移动膝关节的情况下收缩大腿前侧肌肉，维持肌力。', '["平躺，膝下垫一小毛巾卷","收紧大腿前侧肌肉，将膝盖向下压向床面","保持收缩5-10秒，然后放松","换另一条腿重复"]', 10, 15, '保持正常呼吸，不要憋气', '急性期'),
('直腿抬高训练', 'strength', 'medium', '膝关节', '膝关节置换术', '强化股四头肌和髋屈肌，为行走做准备。', '["平躺，健侧腿弯曲踩床","患侧腿保持伸直，脚尖朝上","缓慢抬起患侧腿至约30-45度","保持5秒后缓慢放下"]', 8, 10, '抬腿高度以不引起剧痛为度', '恢复期'),
('靠墙静蹲', 'strength', 'medium', '膝关节', '膝关节置换术', '增强下肢力量，改善膝关节稳定性。', '["背靠墙壁站立，双脚与肩同宽","缓慢下滑至半蹲位，膝盖不超过脚尖","保持30-60秒","缓慢站起恢复"]', 5, 5, '膝盖屈曲角度不超过90度', '恢复期'),
('上肢拉伸', 'stretching', 'easy', '肩部', '通用', '改善上肢柔韧性，缓解术后肩颈紧张。', '["坐姿，双手交叉抱于胸前","缓慢将双手向上推过头顶","保持15秒后缓慢放下","重复动作"]', 5, 10, '动作轻柔，不要用力过猛', '急性期'),
('腹式呼吸训练', 'breathing', 'easy', '腹部', '通用', '促进放松，改善肺通气，减少术后肺部并发症。', '["平躺或坐姿，一只手放于腹部","用鼻子缓慢吸气，感受腹部隆起","用嘴巴缓慢呼气，感受腹部下沉","保持呼吸均匀"]', 5, 10, '如有头晕请暂停休息', '急性期'),
('坐位体前屈', 'stretching', 'easy', '腰部', '腰椎间盘手术', '温和拉伸腰背部和腿后侧肌群。', '["坐于床沿，双脚平放地面","缓慢前倾上身，手臂向前伸展","感受腰背部轻拉伸感，保持15秒","缓慢回到起始位置"]', 5, 8, '避免弹震式拉伸，动作缓慢匀速', '恢复期'),
('平衡站立训练', 'balance', 'medium', '下肢', '通用', '改善站立平衡能力，预防跌倒。', '["双脚并拢站立，可手扶稳固物体","缓慢松开双手，保持平衡","尝试单脚站立5-10秒","换脚重复"]', 5, 6, '确保旁边有稳固支撑物', '恢复期'),
('步行训练', 'mobility', 'medium', '下肢', '通用', '逐步恢复正常步行能力，提高耐力。', '["在平坦地面上，使用辅助器具（如需要）","保持正常步态，脚跟先着地","每次步行10-15分钟","记录步行距离和时间"]', 15, 1, '循序渐进，以不引起过度疲劳为度', '恢复期'),
('八段锦-双手托天', 'stretching', 'easy', '全身', '通用', '传统养生功法，调理三焦，舒展全身。', '["自然站立，双脚与肩同宽","双手掌心向上，从体前缓缓上提","至头顶上方时翻掌上托","保持3-5秒后缓慢下落"]', 3, 6, '动作与呼吸配合，上提时吸气，下落时呼气', '巩固期');
