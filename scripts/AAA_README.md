# Scripts 脚本工具集

本目录包含系统开发、调试和数据初始化所用的各类脚本工具。

---

## 数据初始化 (seed_*)
- `seed_users.py` - 创建3个测试用户（低/中/高风险），包含账号、健康档案和健康评估
- `seed_checkins_low_risk.py` - 向 `test_user` 插入2条低风险打卡数据（生命体征正常）
- `seed_checkins_medium_risk.py` - 向 `test_user_2` 插入2条中风险打卡数据（轻度异常指标）
- `seed_checkins_high_risk.py` - 向 `test_user_3` 插入2条高风险打卡数据（严重异常指标）

## 数据检查 (check_*)
- `check_data_low_risk.py` - 查看 `test_user` 的健康档案、评估和打卡记录
- `check_data_medium_risk.py` - 查看 `test_user_2` 的中风险患者数据
- `check_data_high_risk.py` - 查看 `test_user_3` 的高风险患者数据
- `check_db.py` - 检查 MySQL 表结构及关键表是否存在

## 数据库初始化
- `init_mysql.py` - 初始化 MySQL 数据库（调用 `db_operation.init_database()`）

## 知识图谱 & NER
- `build_up_graph.py` - 向 Neo4j 导入疾病、症状、药品等实体和关系，构建医学知识图谱
- `ner_data.py` - 处理 NER 训练数据，使用 Aho-Corasick 自动机进行字符串匹配

## 语音相关测试
- `convert_audio.py` - 将 MP3 转为单声道 16kHz WAV（供 ASR 使用）
- `test_asr_recognition.py` - 测试阿里云 DashScope Fun-ASR 语音识别 API
- `debug_audio_format.py` - 调试音频格式兼容性
- `debug_mic_audio.py` - 调试麦克风录音音频

## API 连接测试
- `test_deepseek.py` - 测试 DeepSeek API 连接是否正常
- `test_mysql.py` - 测试 MySQL 数据库连接是否正常
- `test_ocr.py` - 测试图片 OCR 文字识别接口

## 测试音频文件
- `标准录音.mp3` - 原始测试音频（MP3）
- `标准录音_mono_16k.wav` - 转换后的测试音频（单声道 16kHz WAV）
