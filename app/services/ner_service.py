import os
import pickle
import torch
from typing import Dict, Optional
from app.core.config import settings
from app.core.logging import get_logger
import sys
from pathlib import Path

logger = get_logger(__name__)

try:
    from . import ner_model as zwk
    from transformers import BertTokenizer, BertModel
except ImportError:
    zwk = None; BertTokenizer = None; BertModel = None

class NERService:
    """实体识别服务"""
    def __init__(self):
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        self.bert_tokenizer = None
        self.bert_model = None
        self.idx2tag = []
        self.rule = None
        self.tfidf_r = None
        self._load_models()

    def _load_models(self):
        """加载 NER 模型及配置"""
        logger.info("loading_ner_models")
        try:
            if zwk and os.path.exists(settings.TAG2IDX_PATH):
                with open(settings.TAG2IDX_PATH, 'rb') as f:
                    tag2idx = pickle.load(f)
                self.idx2tag = list(tag2idx)
                self.rule = zwk.rule_find()
                self.tfidf_r = zwk.tfidf_alignment()
                logger.info("ner_config_loaded")
        except Exception as e:
            logger.error("ner_config_load_failed", error=str(e))

        try:
            if BertTokenizer and BertModel:
                local_path = settings.BERT_MODEL_PATH
                model_name = local_path
                self.bert_tokenizer = BertTokenizer.from_pretrained(model_name)
                
                if zwk and os.path.exists(settings.NER_MODEL_WEIGHTS):
                    self.bert_model = zwk.Bert_Model(model_name, hidden_size=128, tag_num=len(tag2idx), bi=True)
                    self.bert_model.load_state_dict(torch.load(settings.NER_MODEL_WEIGHTS, map_location=self.device))
                    self.bert_model = self.bert_model.to(self.device).eval()
                    logger.info("ner_model_loaded")
        except Exception as e:
            logger.error("ner_model_load_failed", error=str(e))

    def recognize(self, query: str) -> Dict:
        """执行实体识别"""
        if self.bert_model is None or self.bert_tokenizer is None or zwk is None:
            return self._simple_recognize(query)

        try:
            return zwk.get_ner_result(
                self.bert_model, self.bert_tokenizer, query, 
                self.rule, self.tfidf_r, self.device, self.idx2tag
            )
        except Exception as e:
            logger.warning("ner_recognition_fallback", error=str(e))
            return self._simple_recognize(query)

    def _simple_recognize(self, query: str) -> Dict:
        """关键词匹配简易识别"""
        entities = {}
        maps = {
            '疾病': ['感冒', '发烧', '糖尿病', '高血压', '肺炎'],
            '症状': ['头痛', '咳嗽', '疼痛', '恶心'],
            '药品': ['药', '胶囊', '片', '颗粒']
        }
        for tag, keywords in maps.items():
            for k in keywords:
                if k in query: entities[tag] = k; break
        return entities

ner_service = NERService()
