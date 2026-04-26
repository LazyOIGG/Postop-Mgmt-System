import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """项目全局配置"""
    # 基础设置
    PROJECT_NAME: str = "术后管理系统API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # DeepSeek API 配置
    DEEPSEEK_API_KEY: str = "sk-58396912557140d5905f46327db61622"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # Neo4j 配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "GX3216379973.qq"
    NEO4J_NAME: str = "neo4j"
    
    # MySQL 配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "GX3216379973.qq"
    MYSQL_DATABASE: str = "RAG"
    
    # 模型路径配置
    BERT_MODEL_PATH: str = "./model/chinese-roberta-wwm-ext"
    NER_MODEL_WEIGHTS: str = "model/best_roberta_rnn_model_ent_aug.pt"
    TAG2IDX_PATH: str = "tmp_data/tag2idx.npy"
    
    # 安全配置
    SECRET_KEY: str = "YOUR_SECRET_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24小时
    
    # 预留多模态接口
    SPEECH_API_KEY: Optional[str] = None
    IMAGE_API_KEY: Optional[str] = None

    # 阿里云百炼 Fun-ASR 配置
    DASHSCOPE_API_KEY: Optional[str] = "sk-d9a533762e444fd7846a33f16aaf2942"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra='ignore')

settings = Settings()
