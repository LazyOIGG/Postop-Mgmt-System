import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """项目全局配置"""
    # 基础设置
    PROJECT_NAME: str
    VERSION: str
    API_V1_STR: str
    
    # DeepSeek API 配置
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_MODEL: str
    
    # Neo4j 配置
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    NEO4J_NAME: str
    
    # MySQL 配置
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str
    
    # 模型路径配置
    BERT_MODEL_PATH: str
    NER_MODEL_WEIGHTS: str
    TAG2IDX_PATH: str
    
    # 安全配置
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # 默认管理员账户
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""

    # 健康监测阈值
    TEMP_HIGH_RISK: float = 39.0
    TEMP_MEDIUM_RISK: float = 37.8
    BP_SYSTOLIC_HIGH_RISK: int = 180
    BP_DIASTOLIC_HIGH_RISK: int = 120
    BP_SYSTOLIC_MEDIUM_RISK: int = 140
    BP_DIASTOLIC_MEDIUM_RISK: int = 90
    BLOOD_SUGAR_HIGH: float = 11.1
    HEART_RATE_HIGH: int = 120
    HEART_RATE_LOW: int = 50
    
    # 预留多模态接口
    SPEECH_API_KEY: Optional[str] = None
    IMAGE_API_KEY: Optional[str] = None

    # 阿里云百炼 Fun-ASR 配置
    DASHSCOPE_API_KEY: Optional[str] = None

    # 智谱AI配置 (用于 finetune_demo)
    ZHIPUAI_API_KEY: Optional[str] = None

    # ── 会话记忆配置 ──
    MAX_CONVERSATION_HISTORY_TURNS: int = 10
    CONVERSATION_SUMMARY_THRESHOLD_CHARS: int = 3000

    # ── 工具调用配置 ──
    MAX_TOOL_CALL_ROUNDS: int = 3

    # ── 知识图谱增强配置 ──
    KG_MAX_HOPS: int = 3
    KG_VISUALIZE_MAX_NODES: int = 50

    # ── 推送通知配置 ──
    NOTIFICATION_CHECK_INTERVAL: int = 60

    # ── 语音交互配置 ──
    TTS_VOICE: str = "longxiaochun"  # CosyVoice 音色
    TTS_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra='ignore')

settings = Settings()