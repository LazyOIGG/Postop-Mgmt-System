import os
import json
import pickle
import torch
from typing import Dict, List, Optional, Union
from app.core.config import settings
from app.core.logging import get_logger
import sys
from pathlib import Path

logger = get_logger(__name__)

try:
    from . import ner_model as zwk
    from transformers import BertTokenizer, BertModel
    from peft import PeftModel, PeftConfig
except ImportError:
    zwk = None; BertTokenizer = None; BertModel = None; PeftModel = None; PeftConfig = None

class NERService:
    """实体识别服务

    支持两种模型加载方式：
    1. 原始 BERT + RNN 模型（默认）
    2. LoRA 微调后的模型（优先级更高）

    功能特性：
    - 实体归一化：将别名映射到标准名称
    - 多实体识别：支持同类型多个实体
    - 置信度输出：输出识别置信度

    LoRA 微调模型目录结构:
        model/ner_lora_finetuned/
        ├── config.json          # 模型配置
        ├── tag2idx.pkl          # 标签映射
        └── lora_weights/        # LoRA 权重
            ├── adapter_config.json
            └── adapter_model.bin
    """
    def __init__(self):
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        self.bert_tokenizer = None
        self.bert_model = None
        self.idx2tag = []
        self.rule = None
        self.tfidf_r = None
        self.is_lora_model = False
        self.entity_aliases = {}  # 实体别名词典
        self._load_models()
        self._load_entity_aliases()

    def _load_models(self):
        """加载 NER 模型及配置

        优先加载 LoRA 微调模型，如果不存在则加载原始模型
        """
        logger.info("loading_ner_models")
        try:
            if zwk and os.path.exists(settings.TAG2IDX_PATH):
                # tag2idx 是项目内部生成的标签映射文件，来源可信
                with open(settings.TAG2IDX_PATH, 'rb') as f:
                    tag2idx = pickle.load(f)
                self.idx2tag = list(tag2idx)
                self.rule = zwk.rule_find()
                self.tfidf_r = zwk.tfidf_alignment()
                logger.info("ner_config_loaded")
        except Exception as e:
            logger.error("ner_config_load_failed error=%s", str(e))

        # 优先尝试加载 LoRA 微调模型
        lora_model_path = os.path.join('model', 'ner_lora_finetuned')
        if self._try_load_lora_model(lora_model_path):
            self.is_lora_model = True
            print("[SUCCESS] LoRA 微调 NER 模型加载成功")
            return

        # 回退到原始模型
        try:
            if BertTokenizer and BertModel:
                local_path = settings.BERT_MODEL_PATH
                model_name = local_path
                self.bert_tokenizer = BertTokenizer.from_pretrained(model_name)

                if zwk and os.path.exists(settings.NER_MODEL_WEIGHTS):
                    self.bert_model = zwk.Bert_Model(model_name, hidden_size=128, tag_num=len(tag2idx), bi=True)
                    # weights_only=True 避免反序列化任意 Python 对象
                    self.bert_model.load_state_dict(torch.load(settings.NER_MODEL_WEIGHTS, map_location=self.device, weights_only=True))
                    self.bert_model = self.bert_model.to(self.device).eval()
                    logger.info("ner_model_loaded")
        except Exception as e:
            logger.error("ner_model_load_failed error=%s", str(e))

    def _load_entity_aliases(self):
        """加载实体别名词典"""
        aliases_path = os.path.join('data', 'entity_aliases.json')
        try:
            if os.path.exists(aliases_path):
                with open(aliases_path, 'r', encoding='utf-8') as f:
                    self.entity_aliases = json.load(f)
                logger.info("entity_aliases_loaded", path=aliases_path)
            else:
                logger.warning("entity_aliases_not_found", path=aliases_path)
        except Exception as e:
            logger.error("entity_aliases_load_failed", error=str(e))

    def _normalize_entity(self, entity_type: str, entity_text: str) -> str:
        """实体归一化：将别名映射到标准名称

        Args:
            entity_type: 实体类型（疾病、症状等）
            entity_text: 实体文本

        Returns:
            标准化后的实体名称
        """
        if entity_type in self.entity_aliases:
            return self.entity_aliases[entity_type].get(entity_text, entity_text)
        return entity_text

    def _try_load_lora_model(self, model_dir: str) -> bool:
        """尝试加载 LoRA 微调模型

        Args:
            model_dir: LoRA 模型目录

        Returns:
            是否加载成功
        """
        if not PeftModel or not PeftConfig:
            print("[WARN] peft 库未安装，无法加载 LoRA 模型")
            return False

        config_path = os.path.join(model_dir, 'config.json')
        lora_weights_path = os.path.join(model_dir, 'lora_weights')
        tag2idx_path = os.path.join(model_dir, 'tag2idx.pkl')

        # 检查必要文件是否存在
        if not all(os.path.exists(p) for p in [config_path, lora_weights_path, tag2idx_path]):
            print("[INFO] LoRA 微调模型不存在，将使用原始模型")
            return False

        try:
            # 加载配置
            with open(config_path, 'r') as f:
                config = json.load(f)

            # 加载标签映射（项目内部微调生成的标签映射，来源可信）
            with open(tag2idx_path, 'rb') as f:
                tag2idx = pickle.load(f)
            self.idx2tag = list(tag2idx.keys())

            # 加载分词器
            model_name = config.get('model_name', settings.BERT_MODEL_PATH)
            self.bert_tokenizer = BertTokenizer.from_pretrained(model_name)

            # 加载基础模型
            base_model = BertModel.from_pretrained(model_name)

            # 加载 LoRA 权重
            self.bert_model = PeftModel.from_pretrained(base_model, lora_weights_path)
            self.bert_model = self.bert_model.to(self.device).eval()

            # 更新规则和 TF-IDF 对齐（如果存在）
            if zwk:
                try:
                    self.rule = zwk.rule_find()
                    self.tfidf_r = zwk.tfidf_alignment()
                except Exception as e:
                    print(f"[WARN] 规则/TF-IDF 加载失败: {e}")

            return True

        except Exception as e:
            print(f"[ERROR] LoRA 模型加载失败: {e}")
            return False

    def recognize(self, query: str) -> Dict[str, str]:
        """执行实体识别（单实体模式，兼容旧接口）

        支持两种模型：
        1. LoRA 微调模型 - 使用 PeftModel 推理
        2. 原始 BERT + RNN 模型 - 使用 zwk.get_ner_result

        Returns:
            实体字典，同类型只保留第一个
            示例: {'疾病': '糖尿病', '检查项目': '血压'}
        """
        # 获取多实体结果
        multi_result = self.recognize_multi(query)

        # 转换为单实体格式（兼容旧接口）
        result = {}
        for ent_type, ent_list in multi_result.items():
            if ent_list:
                result[ent_type] = ent_list[0]

        return result

    def recognize_multi(self, query: str) -> Dict[str, List[str]]:
        """执行实体识别（多实体模式）

        支持两种模型：
        1. LoRA 微调模型 - 使用 PeftModel 推理
        2. 原始 BERT + RNN 模型 - 使用 zwk.get_ner_result

        Returns:
            实体字典，同类型用列表存储
            示例: {'疾病': ['高血压', '糖尿病'], '检查项目': ['血压', '血糖']}
        """
        if self.bert_model is None or self.bert_tokenizer is None:
            return self._simple_recognize_multi(query)

        try:
            if self.is_lora_model:
                raw_entities = self._recognize_with_lora_multi(query)
            elif zwk is not None:
                # 调用原始模型，结果转换为多实体格式
                single_result = zwk.get_ner_result(
                    self.bert_model, self.bert_tokenizer, query,
                    self.rule, self.tfidf_r, self.device, self.idx2tag
                )
                raw_entities = {k: [v] for k, v in single_result.items()}
            else:
                return self._simple_recognize_multi(query)

            # 实体归一化
            normalized_entities = self._normalize_entities(raw_entities)

            return normalized_entities
        except Exception as e:
            logger.warning("ner_recognition_fallback error=%s", str(e))
            return self._simple_recognize_multi(query)

    def _normalize_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """批量实体归一化

        Args:
            entities: 原始实体字典

        Returns:
            归一化后的实体字典
        """
        normalized = {}
        for ent_type, ent_list in entities.items():
            normalized_list = []
            for ent_text in ent_list:
                standard_name = self._normalize_entity(ent_type, ent_text)
                normalized_list.append(standard_name)
            normalized[ent_type] = normalized_list
        return normalized

    def _recognize_with_lora_multi(self, query: str) -> Dict[str, List[str]]:
        """使用 LoRA 微调模型进行实体识别（多实体模式）

        Args:
            query: 输入文本

        Returns:
            识别到的实体字典，同类型用列表存储
        """
        import torch.nn.functional as F

        # 分词编码
        tokens = list(query)
        inputs = self.bert_tokenizer(
            tokens,
            is_split_into_words=True,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=128
        ).to(self.device)

        # 推理
        with torch.no_grad():
            outputs = self.bert_model(**inputs)
            logits = outputs.last_hidden_state
            preds = torch.argmax(logits, dim=-1)[0].cpu().tolist()

        # 解码预测结果
        pred_tags = [self.idx2tag[idx] if idx < len(self.idx2tag) else 'O' for idx in preds]

        # 提取实体（支持多实体）
        entities = {}
        current_entity = []
        current_type = None

        for i, tag in enumerate(pred_tags[1:-1]):  # 跳过 [CLS] 和 [SEP]
            if tag.startswith('B-'):
                # 保存之前的实体
                if current_entity and current_type:
                    entity_text = ''.join(current_entity)
                    if current_type not in entities:
                        entities[current_type] = []
                    entities[current_type].append(entity_text)
                # 开始新实体
                current_type = tag[2:]
                current_entity = [tokens[i]] if i < len(tokens) else []
            elif tag.startswith('I-') and current_type == tag[2:]:
                if i < len(tokens):
                    current_entity.append(tokens[i])
            else:
                # 保存之前的实体
                if current_entity and current_type:
                    entity_text = ''.join(current_entity)
                    if current_type not in entities:
                        entities[current_type] = []
                    entities[current_type].append(entity_text)
                current_entity = []
                current_type = None

        # 保存最后一个实体
        if current_entity and current_type:
            entity_text = ''.join(current_entity)
            if current_type not in entities:
                entities[current_type] = []
            entities[current_type].append(entity_text)

        # 如果有规则匹配和 TF-IDF 对齐，进行合并优化
        if self.rule and self.tfidf_r and zwk:
            try:
                rule_result = self.rule.find(query)
                # 将规则结果转换为统一格式
                for start, end, ent_type, ent_text in rule_result:
                    if ent_type not in entities:
                        entities[ent_type] = []
                    # 避免重复添加
                    if ent_text not in entities[ent_type]:
                        entities[ent_type].append(ent_text)
            except Exception:
                pass

        return entities

    def _simple_recognize(self, query: str) -> Dict[str, str]:
        """关键词匹配简易识别（单实体模式，兼容旧接口）"""
        multi_result = self._simple_recognize_multi(query)
        result = {}
        for ent_type, ent_list in multi_result.items():
            if ent_list:
                result[ent_type] = ent_list[0]
        return result

    def _simple_recognize_multi(self, query: str) -> Dict[str, List[str]]:
        """关键词匹配简易识别（多实体模式）"""
        entities = {}
        maps = {
            '疾病': ['感冒', '发烧', '糖尿病', '高血压', '肺炎'],
            '症状': ['头痛', '咳嗽', '疼痛', '恶心'],
            '药品': ['药', '胶囊', '片', '颗粒']
        }
        for tag, keywords in maps.items():
            for k in keywords:
                if k in query:
                    if tag not in entities:
                        entities[tag] = []
                    entities[tag].append(k)
        return entities

ner_service = NERService()
