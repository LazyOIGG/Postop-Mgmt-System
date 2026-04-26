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
    
    # 预留多模态接口
    SPEECH_API_KEY: Optional[str] = None
    IMAGE_API_KEY: Optional[str] = None

    # 阿里云百炼 Fun-ASR 配置
    DASHSCOPE_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra='ignore')

settings = Settings()