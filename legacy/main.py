from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import json
import os
import sys
import pickle
import torch
import re
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
import random
import asyncio

from starlette.responses import StreamingResponse

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 尝试导入本地模块
try:
    import ner_model as zwk  # 假设 ner_model 是您的实体识别模块
    from transformers import BertTokenizer, BertModel
    print("成功导入本地模块")
except ImportError as e:
    print(f"导入本地模块失败: {e}")
    zwk = None
    BertTokenizer = None
    BertModel = None

# 导入数据库模块
try:
    # 尝试从 database 子目录导入
    from database.local_db_utils import DatabaseConnector

    # 尝试导入 password_utils，先从当前目录，然后从 database 目录
    try:
        from password_utils import encrypt_password, verify_password, verify_password_strength
    except ImportError:
        # 如果在当前目录找不到，尝试从 database 目录导入
        from database.password_utils import encrypt_password, verify_password, verify_password_strength

    print("成功导入数据库模块")
except ImportError as e:
    print(f"导入数据库模块失败: {e}")
    # 创建虚拟类
    class DatabaseConnector:
        def __init__(self, **kwargs):
            pass
        def connect(self):
            return False
        def close(self):
            pass
        def check_user_exists(self, username):
            return False
        def create_session(self, username, title="新对话"):
            return None
        def save_message(self, session_id, username, role, content, entities=None, intents=None, knowledge=None):
            return False
        def get_user_sessions(self, username):
            return []
        def get_session_messages(self, session_id, username=None):
            return []
        def update_session_title(self, session_id, new_title):
            return False
        def delete_session(self, session_id, username=None):
            return False

    def encrypt_password(password):
        return password

    def verify_password(input_password, stored_hash):
        return input_password == stored_hash

    def verify_password_strength(password):
        return True, "OK"

# 加载环境变量
load_dotenv()

# 初始化DeepSeek客户端 (使用OpenAI兼容接口)
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 初始化FastAPI应用
app = FastAPI(
    title="术后管理系统API",
    description="集成知识图谱和聊天历史的术后管理系统",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接实例
db = DatabaseConnector()

# ============ 数据模型定义 ============
class ChatRequest(BaseModel):
    message: str
    model_choice: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    session_id: Optional[int] = None
    stream: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str

class SessionCreateRequest(BaseModel):
    username: str
    session_title: Optional[str] = "新对话"

class SessionUpdateRequest(BaseModel):
    session_id: int
    new_title: str

class MessageRequest(BaseModel):
    session_id: int
    username: str
    role: str
    content: str
    entities: Optional[str] = None
    intents: Optional[str] = None
    knowledge: Optional[str] = None

class UserStatsRequest(BaseModel):
    username: str

class KnowledgeGraphQuery(BaseModel):
    cypher_query: str
    limit: int = 100

# ============ 用户令牌管理 ============
# 简单的内存令牌存储（生产环境应使用Redis等）
user_tokens = {}

def generate_token(username: str) -> str:
    """生成用户令牌"""
    import secrets
    token = secrets.token_urlsafe(32)
    user_tokens[token] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    return token

def validate_token(token: str) -> Optional[Dict]:
    """验证用户令牌"""
    if token not in user_tokens:
        return None

    user_data = user_tokens[token]
    if datetime.now() > user_data["expires_at"]:
        # 令牌过期
        del user_tokens[token]
        return None

    return user_data

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权的访问")

    token = authorization.replace("Bearer ", "")
    user_data = validate_token(token)

    if not user_data:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    return user_data

# ============ 模型加载 ============
bert_tokenizer = None
bert_model = None
idx2tag = []
rule = None
tfidf_r = None
device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
neo4j_client = None

def load_models():
    """加载所有需要的模型"""
    global bert_tokenizer, bert_model, idx2tag, rule, tfidf_r, neo4j_client

    print("开始加载模型...")

    # 1. 加载BERT模型用于实体识别
    try:
        if zwk and os.path.exists('tmp_data/tag2idx.npy'):
            with open('tmp_data/tag2idx.npy', 'rb') as f:
                tag2idx = pickle.load(f)
            idx2tag = list(tag2idx)
            rule = zwk.rule_find()
            tfidf_r = zwk.tfidf_alignment()
            print("✅ 加载实体识别配置文件成功")
        else:
            print("⚠️ 实体识别配置文件不存在，使用简化版本")
    except Exception as e:
        print(f"❌ 加载实体识别配置文件失败: {e}")

    # 2. 加载BERT模型
    try:
        if BertTokenizer and BertModel:
            # 优先使用本地模型
            local_path = './model/chinese-roberta-wwm-ext'
            model_name = local_path
            
            try:
                bert_tokenizer = BertTokenizer.from_pretrained(model_name)
                base_bert_model = BertModel.from_pretrained(model_name)
                print(f"✅ 加载BERT模型成功，使用{'本地模型' if os.path.exists(local_path) else '在线模型'}")

                # 加载实体识别模型
                if zwk and os.path.exists('model/best_roberta_rnn_model_ent_aug.pt'):
                    # 使用与基础模型相同的路径
                    bert_model = zwk.Bert_Model(model_name, hidden_size=128, tag_num=len(tag2idx), bi=True)
                    bert_model.load_state_dict(torch.load('model/best_roberta_rnn_model_ent_aug.pt', map_location=device))
                    bert_model = bert_model.to(device)
                    bert_model.eval()
                    print("✅ 加载实体识别模型成功")
            except Exception as e:
                print(f"❌ 加载模型失败: {e}")
    except Exception as e:
        print(f"❌ 加载BERT模型失败: {e}")

    # 3. 连接Neo4j
    try:
        import py2neo
        neo4j_client = py2neo.Graph('bolt://localhost:7687', user='neo4j', password='GX3216379973.qq', name='neo4j')
        print("✅ Neo4j连接成功")
    except Exception as e:
        print(f"❌ Neo4j连接失败: {e}")
        neo4j_client = None

    print("模型加载完成")

# ============ 实体识别函数 ============
def entity_recognition(query: str) -> Dict:
    """使用BERT模型进行实体识别"""
    if bert_model is None or bert_tokenizer is None or zwk is None:
        # 使用简化的实体识别
        return simple_entity_recognition(query)

    try:
        entities = zwk.get_ner_result(bert_model, bert_tokenizer, query, rule, tfidf_r, device, idx2tag)
        return entities
    except Exception as e:
        print(f"实体识别失败: {e}，使用简化版本")
        return simple_entity_recognition(query)

def simple_entity_recognition(query: str) -> Dict:
    """简化的实体识别函数"""
    entities = {}

    # 简单的关键词匹配
    disease_keywords = ['感冒', '发烧', '头痛', '糖尿病', '高血压', '癌症', '肺炎', '心脏病', '胃病', '肝病']
    symptom_keywords = ['症状', '头痛', '发热', '咳嗽', '疼痛', '恶心', '呕吐', '腹泻', '头晕', '乏力']
    medicine_keywords = ['药', '药品', '胶囊', '片', '丸', '颗粒', '口服液']
    food_keywords = ['食物', '吃', '饮食', '水果', '蔬菜', '肉']
    exam_keywords = ['检查', '化验', '体检', 'CT', 'B超', 'X光']

    # 查找疾病
    for keyword in disease_keywords:
        if keyword in query:
            entities['疾病'] = keyword
            break

    # 查找症状
    for keyword in symptom_keywords:
        if keyword in query:
            entities['症状'] = keyword
            break

    # 查找药品
    for keyword in medicine_keywords:
        if keyword in query:
            entities['药品'] = keyword
            break

    # 查找食物
    for keyword in food_keywords:
        if '宜吃' in query or '适合吃' in query:
            if keyword in query:
                entities['宜吃食物'] = keyword
        elif '忌吃' in query or '不能吃' in query:
            if keyword in query:
                entities['忌吃食物'] = keyword

    # 查找检查项目
    for keyword in exam_keywords:
        if keyword in query:
            entities['检查项目'] = keyword
            break

    return entities

# ============ 意图识别函数 ============
def intent_recognition(query: str, model_choice: str = None) -> str:
    """使用DeepSeek进行意图识别"""
    # 确保使用正确的模型，如果传入的是旧的Ollama模型名，则替换为DeepSeek模型
    if model_choice is None or ":" in model_choice or "qwen" in model_choice.lower():
        model_choice = DEEPSEEK_MODEL

    prompt = f"""
阅读下列提示，回答问题（问题在输入的最后）:
当你试图识别用户问题中的查询意图时，你需要仔细分析问题，并在16个预定义的查询类别中一一进行判断。

**查询类别**
- "查询疾病简介"
- "查询疾病病因"
- "查询疾病预防措施"
- "查询疾病治疗周期"
- "查询治愈概率"
- "查询疾病易感人群"
- "查询疾病所需药品"
- "查询疾病宜吃食物"
- "查询疾病忌吃食物"
- "查询疾病所需检查项目"
- "查询疾病所属科目"
- "查询疾病的症状"
- "查询疾病的治疗方法"
- "查询疾病的并发疾病"
- "查询药品的生产商"

在处理用户的问题时，请按照以下步骤操作：
1. 仔细阅读用户的问题
2. 对照上述查询类别列表，依次考虑每个类别是否与用户问题相关
3. 如果用户问题明确或隐含地包含了某个类别的查询意图，请将该类别的描述添加到输出列表中
4. 确保最终的输出列表包含了所有与用户问题相关的类别描述

**注意：**
- 你的所有输出都必须在这个范围上述**查询类别**范围内，不可创造新的名词与类别！
- 你的输出的类别数量不应该超过5个，如果确实有很多个，请你输出最有可能的5个！
- 请在输出查询意图对应的列表之后，用"#"号开始的注释，简短地解释为什么选择这些意图选项

现在，问题输入："{query}"
输出的时候请确保输出内容都在**查询类别**中出现过。
"""
    try:
        response = deepseek_client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}]
        )
        rec_result = response.choices[0].message.content
        return rec_result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"意图识别失败: {str(e)}\n{error_details}")
        return "[] # 意图识别失败"

# ============ 知识图谱辅助函数 ============
def add_shuxing_prompt(entity, shuxing, client):
    """添加属性提示"""
    if client is None:
        return ""

    add_prompt = ""
    try:
        sql_q = "match (a:疾病{名称:'%s'}) return a.%s" % (entity, shuxing)
        res = client.run(sql_q).data()[0].values()
        add_prompt += "<提示>"
        add_prompt += f"用户对{entity}可能有查询{shuxing}需求，知识库内容如下："
        if len(res) > 0:
            join_res = "".join(res)
            add_prompt += join_res
        else:
            add_prompt += "图谱中无信息，查找失败。"
        add_prompt += "</提示>"
    except Exception as e:
        print(f"添加属性提示失败: {e}")
    return add_prompt

def add_lianxi_prompt(entity, lianxi, target, client):
    """添加联系提示"""
    if client is None:
        return ""

    add_prompt = ""
    try:
        sql_q = "match (a:疾病{名称:'%s'})-[r:%s]->(b:%s) return b.名称" % (entity, lianxi, target)
        res = client.run(sql_q).data()
        res = [list(data.values())[0] for data in res]
        add_prompt += "<提示>"
        add_prompt += f"用户对{entity}可能有查询{lianxi}需求，知识库内容如下："
        if len(res) > 0:
            join_res = "、".join(res)
            add_prompt += join_res
        else:
            add_prompt += "图谱中无信息，查找失败。"
        add_prompt += "</提示>"
    except Exception as e:
        print(f"添加联系提示失败: {e}")
    return add_prompt

def generate_enhanced_prompt(intent_response: str, query: str, entities: Dict) -> tuple:
    """生成增强提示文本，结合Neo4j结果和大模型润色"""
    # 1. 首先获取Neo4j查询结果
    neo4j_prompt = '<指令>你是一个医疗问答机器人，你需要根据给定的提示回答用户的问题。请注意，你的全部回答必须完全基于给定的提示，不可自由发挥。如果根据提示无法给出答案，立刻回答"根据已知信息无法回答该问题"。</指令>'
    neo4j_prompt += '<指令>请你仅针对医疗类问题提供简洁和专业的回答。如果问题不是医疗相关的，你一定要回答"我只能回答医疗相关的问题。"，以明确告知你的回答限制。</指令>'
    
    # 添加症状推测逻辑
    has_neo4j_results = False
    
    if '疾病症状' in entities and '疾病' not in entities and neo4j_client is not None:
        try:
            sql_q = "match (a:疾病)-[r:疾病的症状]->(b:疾病症状 {名称:'%s'}) return a.名称" % (entities['疾病症状'])
            res = list(neo4j_client.run(sql_q).data()[0].values())
            if len(res) > 0:
                has_neo4j_results = True
                entities['疾病'] = random.choice(res)
                all_en = "、".join(res)
                neo4j_prompt += f"<提示>用户有{entities['疾病症状']}的情况，知识库推测其可能是得了{all_en}。请注意这只是一个推测，你需要明确告知用户这一点。</提示>"
        except Exception as e:
            print(f"症状推测失败: {e}")
    
    pre_len = len(neo4j_prompt)
    yitu = []
    
    # 根据意图添加知识库信息
    intent_mappings = {
        "简介": ("查询疾病简介", "疾病简介", None),
        "病因": ("查询疾病病因", "疾病病因", None),
        "预防": ("查询疾病预防措施", "预防措施", None),
        "治疗周期": ("查询疾病治疗周期", "治疗周期", None),
        "治愈概率": ("查询治愈概率", "治愈概率", None),
        "易感人群": ("查询疾病易感人群", "疾病易感人群", None),
        "药品": ("查询疾病所需药品", "疾病使用药品", "药品"),
        "宜吃食物": ("查询疾病宜吃食物", "疾病宜吃食物", "食物"),
        "忌吃食物": ("查询疾病忌吃食物", "疾病忌吃食物", "食物"),
        "检查项目": ("查询疾病所需检查项目", "疾病所需检查", "检查项目"),
        "所属科目": ("查询疾病所属科目", "疾病所属科目", "科目"),
        "症状": ("查询疾病的症状", "疾病的症状", "疾病症状"),
        "治疗": ("查询疾病的治疗方法", "治疗的方法", "治疗方法"),
        "并发": ("查询疾病的并发疾病", "疾病并发疾病", "疾病"),
        "生产商": ("查询药品的生产商", None, None)
    }
    
    # 提取意图关键词
    intent_response_lower = intent_response.lower()
    
    for key, (intent, prop, target) in intent_mappings.items():
        if key in intent_response_lower and '疾病' in entities:
            if key == "生产商" and '药品' in entities and neo4j_client is not None:
                try:
                    sql_q = "match (a:药品商)-[r:生产]->(b:药品{名称:'%s'}) return a.名称" % (entities['药品'])
                    res = neo4j_client.run(sql_q).data()[0].values()
                    neo4j_prompt += "<提示>"
                    neo4j_prompt += f"用户对{entities['药品']}可能有查询药品生产商的需求，知识图谱内容如下："
                    if len(res) > 0:
                        has_neo4j_results = True
                        neo4j_prompt += "".join(res)
                    else:
                        neo4j_prompt += "图谱中无信息，查找失败"
                    neo4j_prompt += "</提示>"
                    yitu.append(intent)
                except Exception as e:
                    print(f"查询药品生产商失败: {e}")
            elif prop and target and neo4j_client is not None:
                temp_prompt = add_lianxi_prompt(entities['疾病'], prop, target, neo4j_client)
                neo4j_prompt += temp_prompt
                if "查找失败" not in temp_prompt:
                    has_neo4j_results = True
                yitu.append(intent)
            elif prop and neo4j_client is not None:
                temp_prompt = add_shuxing_prompt(entities['疾病'], prop, neo4j_client)
                neo4j_prompt += temp_prompt
                if "查找失败" not in temp_prompt:
                    has_neo4j_results = True
                yitu.append(intent)
    
    # 2. 生成增强提示
    if has_neo4j_results:
        # 如果有Neo4j结果，使用大模型润色
        enhanced_prompt = '<指令>你是一个医疗问答机器人，你需要根据给定的提示回答用户的问题。</指令>'
        enhanced_prompt += '<指令>你需要以专业的医疗知识为基础，将提示中的内容整理成结构清晰、信息有条理、内容丰富、解释详细的专业回答。</指令>'
        enhanced_prompt += '<指令>请你仅针对医疗类问题提供回答。如果问题不是医疗相关的，你一定要回答"我只能回答医疗相关的问题。"，以明确告知你的回答限制。</指令>'
        enhanced_prompt += neo4j_prompt[neo4j_prompt.find('<提示>'):]  # 只保留提示部分
        enhanced_prompt += f'<用户问题>{query}</用户问题>'
        enhanced_prompt += '<注意>你需要以提示中的知识为基础，对其进行润色和组织，但不可添加提示之外的医疗信息。</注意>'
        enhanced_prompt += '<注意>请按照逻辑层次组织回答，使用自然的分段和序号，不要使用Markdown格式（如"- **"等特殊字符）。</注意>'
        enhanced_prompt += '<注意>对关键医疗术语进行简要解释，使内容更易懂。</注意>'
        enhanced_prompt += '<注意>提供更详细的医学解释和建议，使回答更符合临床实践。</注意>'
        enhanced_prompt += '<注意>确保回答专业、准确、有条理，符合医疗领域的表达习惯。</注意>'
        enhanced_prompt += '<注意>请在回答的最后标注"(本回答基于知识图谱生成)"。</注意>'
    else:
        # 如果没有Neo4j结果，使用大模型生成并标注
        enhanced_prompt = '<指令>你是一个医疗问答机器人，你需要根据用户的问题提供专业的回答。</指令>'
        enhanced_prompt += '<指令>由于知识库中没有找到相关信息，你需要直接回答用户的问题，但请确保回答准确可靠。</指令>'
        enhanced_prompt += '<指令>请在回答的最后标注"(本回答由大语言模型生成)"。</指令>'
        enhanced_prompt += '<指令>请你仅针对医疗类问题提供简洁和专业的回答。如果问题不是医疗相关的，你一定要回答"我只能回答医疗相关的问题。"，以明确告知你的回答限制。</指令>'
        enhanced_prompt += f'<用户问题>{query}</用户问题>'
        enhanced_prompt += '<注意>你的回答必须专业、准确、有条理，符合医疗领域的表达习惯。</注意>'
    
    print(f'生成的增强提示长度: {len(enhanced_prompt)} 字符')
    print(f'是否有Neo4j结果: {has_neo4j_results}')
    return enhanced_prompt, "、".join(yitu), entities, has_neo4j_results

def generate_prompt(intent_response: str, query: str, entities: Dict) -> tuple:
    """生成提示文本（兼容原有接口）"""
    prompt, yitu, entities, _ = generate_enhanced_prompt(intent_response, query, entities)
    return prompt, yitu, entities

# ============ 聊天处理函数 ============
async def process_chat_message(query: str, model_choice: str = None) -> Dict:
    """处理聊天消息的核心函数"""
    # 确保使用正确的模型，如果传入的是旧的Ollama模型名，则替换为DeepSeek模型
    if model_choice is None or ":" in model_choice or "qwen" in model_choice.lower():
        model_choice = DEEPSEEK_MODEL

    try:
        print(f"处理消息: {query}")

        # 实体识别
        entities = entity_recognition(query)
        print(f"识别到的实体: {entities}")

        # 意图识别
        intent_response = intent_recognition(query, model_choice)
        print(f"意图识别结果: {intent_response}")

        # 生成提示
        prompt, yitu, entities = generate_prompt(intent_response, query, entities)

        # 调用DeepSeek生成回复
        try:
            full_response = ""
            response = deepseek_client.chat.completions.create(
                model=model_choice,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"DeepSeek调用失败: {str(e)}\n{error_details}")
            full_response = f"抱歉，AI服务暂时不可用。错误详情: {str(e)}"

        # 提取知识库信息
        knowledge = re.findall(r'<提示>(.*?)</提示>', prompt)
        zhishiku_content = "\n".join([f"提示{idx + 1}: {kn}" for idx, kn in enumerate(knowledge) if len(kn) >= 3])

        return {
            "content": full_response,
            "entities": str(entities),
            "intents": yitu,
            "knowledge": zhishiku_content
        }

    except Exception as e:
        print(f"处理消息时出错: {str(e)}")
        return {
            "content": f"抱歉，处理请求时出现错误: {str(e)}",
            "entities": "{}",
            "intents": "",
            "knowledge": ""
        }

# ============ WebSocket连接管理 ============
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# ============ API端点 ============
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "术后管理系统API服务运行中",
        "version": "2.0.0",
        "status": "healthy",
        "endpoints": [
            "/docs - API文档",
            "/api/health - 健康检查",
            "/api/chat - 聊天接口",
            "/api/login - 用户登录",
            "/api/register - 用户注册",
            "/ws - WebSocket连接"
        ]
    }

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    db_status = "connected" if db.connection and db.connection.is_connected() else "disconnected"
    neo4j_status = "connected" if neo4j_client else "disconnected"
    model_status = "loaded" if bert_tokenizer else "not_loaded"

    return {
        "status": "healthy",
        "service": "medical-qa-api",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "neo4j": neo4j_status,
        "model": model_status,
        "llm": "deepseek" if deepseek_client.api_key else "unavailable"
    }

# ============ 用户认证API ============
@app.post("/api/login")
async def login(request: LoginRequest):
    """用户登录"""
    try:
        # 连接到数据库
        if not db.connect():
            raise HTTPException(status_code=500, detail="数据库连接失败")

        # 查询用户
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT username, password, is_admin FROM users WHERE username = %s",
            (request.username,)
        )
        user = cursor.fetchone()
        cursor.close()

        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 验证密码
        if not verify_password(request.password, user['password']):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 生成token
        token = generate_token(user['username'])

        return {
            "success": True,
            "username": user['username'],
            "is_admin": user['is_admin'] == 1,
            "token": token,
            "message": "登录成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"登录失败: {e}")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.post("/api/register")
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        # 验证密码
        if request.password != request.confirm_password:
            raise HTTPException(status_code=400, detail="两次输入的密码不一致")

        # 验证密码强度
        strength_ok, strength_msg = verify_password_strength(request.password)
        if not strength_ok:
            raise HTTPException(status_code=400, detail=f"密码强度不足: {strength_msg}")

        # 连接到数据库
        if not db.connect():
            raise HTTPException(status_code=500, detail="数据库连接失败")

        # 检查用户名是否已存在
        if db.check_user_exists(request.username):
            raise HTTPException(status_code=400, detail="用户名已存在")

        # 加密密码
        encrypted_pwd = encrypt_password(request.password)

        # 创建用户
        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, 0)",
            (request.username, encrypted_pwd)
        )
        db.connection.commit()
        cursor.close()

        return {
            "success": True,
            "message": f"用户 {request.username} 注册成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"注册失败: {e}")
        if db.connection:
            db.connection.rollback()
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

# ============ 会话管理API ============
@app.post("/api/sessions/create")
async def create_session(request: SessionCreateRequest, user: Dict = Depends(get_current_user)):
    """创建新的聊天会话"""
    try:
        if user["username"] != request.username:
            raise HTTPException(status_code=403, detail="无权为该用户创建会话")

        session_id = db.create_session(request.username, request.session_title)
        if not session_id:
            raise HTTPException(status_code=500, detail="创建会话失败")

        return {
            "success": True,
            "session_id": session_id,
            "session_title": request.session_title,
            "message": "会话创建成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

@app.get("/api/sessions/user/{username}")
async def get_user_sessions(username: str, user: Dict = Depends(get_current_user)):
    """获取用户的所有会话"""
    try:
        if user["username"] != username:
            raise HTTPException(status_code=403, detail="无权查看该用户的会话")

        sessions = db.get_user_sessions(username)
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")

@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, username: Optional[str] = None,
                               user: Dict = Depends(get_current_user)):
    """获取会话的所有消息"""
    try:
        if username and user["username"] != username:
            raise HTTPException(status_code=403, detail="无权查看该会话")

        messages = db.get_session_messages(session_id, username)
        return {
            "success": True,
            "messages": messages,
            "count": len(messages)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"获取消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取消息失败: {str(e)}")

@app.put("/api/sessions/rename")
async def rename_session(request: SessionUpdateRequest, user: Dict = Depends(get_current_user)):
    """重命名会话"""
    try:
        # 验证用户对会话的权限
        session_info = db.get_session_info(request.session_id)
        if not session_info or session_info['username'] != user["username"]:
            raise HTTPException(status_code=403, detail="无权修改此会话")

        success = db.update_session_title(request.session_id, request.new_title)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或重命名失败")

        return {
            "success": True,
            "message": "会话重命名成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"重命名失败: {e}")
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int, username: Optional[str] = None,
                         user: Dict = Depends(get_current_user)):
    """删除会话"""
    try:
        if username and user["username"] != username:
            raise HTTPException(status_code=403, detail="无权删除该会话")

        success = db.delete_session(session_id, username)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或删除失败")

        return {
            "success": True,
            "message": "会话删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

# ============ 消息管理API ============
@app.post("/api/messages/save")
async def save_message(request: MessageRequest, user: Dict = Depends(get_current_user)):
    """保存消息到数据库"""
    try:
        if user["username"] != request.username:
            raise HTTPException(status_code=403, detail="无权保存消息")

        success = db.save_message(
            request.session_id,
            request.username,
            request.role,
            request.content,
            request.entities,
            request.intents,
            request.knowledge
        )

        if not success:
            raise HTTPException(status_code=500, detail="保存消息失败")

        return {
            "success": True,
            "message": "消息保存成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"保存消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存消息失败: {str(e)}")

# ============ 聊天API ============
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, user: Dict = Depends(get_current_user)):
    """聊天接口，支持流式和非流式响应"""
    try:
        username = user["username"]
        session_id = request.session_id

        # 1. 保存用户消息到数据库
        if session_id:
            db.save_message(
                session_id=session_id,
                username=username,
                role="user",
                content=request.message
            )
        else:
            # 如果没有session_id，创建新的会话
            session_id = db.create_session(username, request.message[:30] + "...")
            if session_id:
                db.save_message(
                    session_id=session_id,
                    username=username,
                    role="user",
                    content=request.message
                )

        # 2. 处理消息
        if request.stream:
            # 流式响应
            async def generate():
                # 发送初始响应
                yield json.dumps({
                    "type": "start",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }) + "\n"

                # 处理消息并流式返回
                full_response = ""
                try:
                    # 实体识别
                    entities = entity_recognition(request.message)

                    # 意图识别
                    intent_response = intent_recognition(request.message, request.model_choice)

                    # 生成提示
                    prompt, yitu, entities = generate_prompt(intent_response, request.message, entities)

                    # 确保使用正确的模型
                    model_to_use = request.model_choice
                    if ":" in model_to_use or "qwen" in model_to_use.lower():
                        model_to_use = DEEPSEEK_MODEL

                    # 流式调用DeepSeek
                    response = deepseek_client.chat.completions.create(
                        model=model_to_use,
                        messages=[{'role': 'user', 'content': prompt}],
                        stream=True
                    )
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            content_chunk = chunk.choices[0].delta.content
                            full_response += content_chunk

                            # 发送内容块
                            yield json.dumps({
                                "type": "chunk",
                                "content": content_chunk
                            }) + "\n"

                    # 发送完成信号
                    yield json.dumps({
                        "type": "complete",
                        "entities": str(entities),
                        "intents": yitu
                    }) + "\n"

                    # 保存助手回复到数据库
                    if session_id:
                        # 提取知识库信息
                        knowledge = re.findall(r'<提示>(.*?)</提示>', prompt)
                        zhishiku_content = "\n".join([f"提示{idx + 1}: {kn}" for idx, kn in enumerate(knowledge) if len(kn) >= 3])

                        db.save_message(
                            session_id=session_id,
                            username=username,
                            role="assistant",
                            content=full_response,
                            entities=str(entities),
                            intents=yitu,
                            knowledge=zhishiku_content
                        )

                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"处理失败: {str(e)}\n{error_details}")
                    error_msg = f"处理失败: {str(e)}"
                    yield json.dumps({
                        "type": "error",
                        "error": error_msg
                    }) + "\n"

            return StreamingResponse(generate(), media_type="text/event-stream")

        else:
            # 非流式响应
            result = await process_chat_message(request.message, request.model_choice)

            # 保存助手回复到数据库
            if session_id:
                db.save_message(
                    session_id=session_id,
                    username=username,
                    role="assistant",
                    content=result["content"],
                    entities=result["entities"],
                    intents=result["intents"],
                    knowledge=result["knowledge"]
                )

            return {
                "success": True,
                "content": result["content"],
                "entities": result["entities"],
                "intents": result["intents"],
                "knowledge": result["knowledge"],
                "session_id": session_id
            }

    except Exception as e:
        print(f"聊天接口错误: {str(e)}")
        return {
            "success": False,
            "content": f"抱歉，处理请求时出现错误: {str(e)}",
            "entities": "{}",
            "intents": "",
            "knowledge": "",
            "session_id": request.session_id if request.session_id else None
        }

# ============ WebSocket API ============
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket聊天接口"""
    await manager.connect(websocket)

    try:
        # 验证token
        user_data = None
        if token:
            user_data = validate_token(token)

        if not user_data:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "未授权连接"
            }))
            await websocket.close()
            return

        username = user_data["username"]

        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "连接成功",
            "username": username
        }))

        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data.get("type") == "chat":
                query = message_data.get("message", "")
                model_choice = message_data.get("model_choice", DEEPSEEK_MODEL)
                session_id = message_data.get("session_id")

                if not query:
                    continue

                # 处理消息
                result = await process_chat_message(query, model_choice)

                # 发送结果
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "content": result["content"],
                    "entities": result["entities"],
                    "intents": result["intents"],
                    "knowledge": result["knowledge"]
                }))

                # 保存到数据库（如果提供了session_id）
                if session_id:
                    # 保存用户消息
                    db.save_message(
                        session_id=session_id,
                        username=username,
                        role="user",
                        content=query
                    )

                    # 保存助手回复
                    db.save_message(
                        session_id=session_id,
                        username=username,
                        role="assistant",
                        content=result["content"],
                        entities=result["entities"],
                        intents=result["intents"],
                        knowledge=result["knowledge"]
                    )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"客户端断开连接")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"处理错误: {str(e)}"
            }))
        except:
            pass
        manager.disconnect(websocket)

# ============ 知识图谱API ============
@app.post("/api/kg/query")
async def kg_query(request: KnowledgeGraphQuery, user: Dict = Depends(get_current_user)):
    """查询知识图谱"""
    try:
        if neo4j_client is None:
            raise HTTPException(status_code=500, detail="Neo4j连接不可用")

        # 执行Cypher查询
        results = neo4j_client.run(request.cypher_query).data()

        return {
            "success": True,
            "query": request.cypher_query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        print(f"知识图谱查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.get("/api/kg/diseases")
async def get_diseases(user: Dict = Depends(get_current_user)):
    """获取所有疾病列表"""
    try:
        if neo4j_client is None:
            return {
                "success": True,
                "diseases": [],
                "count": 0,
                "message": "Neo4j不可用"
            }

        query = "MATCH (n:疾病) RETURN n.名称 as name LIMIT 100"
        results = neo4j_client.run(query).data()
        diseases = [r['name'] for r in results if 'name' in r]

        return {
            "success": True,
            "diseases": diseases,
            "count": len(diseases)
        }

    except Exception as e:
        print(f"获取疾病列表失败: {e}")
        return {
            "success": False,
            "diseases": [],
            "count": 0,
            "message": f"获取失败: {str(e)}"
        }

# ============ 统计API ============
@app.get("/api/stats/user/{username}")
async def get_user_stats(username: str, user: Dict = Depends(get_current_user)):
    """获取用户统计信息"""
    try:
        if user["username"] != username:
            raise HTTPException(status_code=403, detail="无权查看该用户的统计信息")

        # 这里可以添加更复杂的统计逻辑
        sessions = db.get_user_sessions(username)
        total_messages = 0

        for session in sessions:
            messages = db.get_session_messages(session['session_id'], username)
            total_messages += len(messages)

        return {
            "success": True,
            "username": username,
            "session_count": len(sessions),
            "total_messages": total_messages,
            "last_active": sessions[0]['last_updated'] if sessions else None
        }

    except Exception as e:
        print(f"获取用户统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@app.get("/api/stats/system")
async def get_system_stats(user: Dict = Depends(get_current_user)):
    """获取系统统计信息（仅管理员）"""
    try:
        # 检查是否为管理员
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT is_admin FROM users WHERE username = %s",
            (user["username"],)
        )
        user_info = cursor.fetchone()
        cursor.close()

        if not user_info or user_info['is_admin'] != 1:
            raise HTTPException(status_code=403, detail="需要管理员权限")

        # 获取系统统计
        stats = {
            "total_users": 0,
            "total_sessions": 0,
            "total_messages": 0,
            "active_today": 0
        }

        try:
            cursor = db.connection.cursor(dictionary=True)

            # 总用户数
            cursor.execute("SELECT COUNT(*) as count FROM users")
            stats["total_users"] = cursor.fetchone()['count']

            # 总会话数
            cursor.execute("SELECT COUNT(*) as count FROM chat_sessions")
            stats["total_sessions"] = cursor.fetchone()['count']

            # 总消息数
            cursor.execute("SELECT COUNT(*) as count FROM user_conversations")
            stats["total_messages"] = cursor.fetchone()['count']

            # 今日活跃用户
            cursor.execute("""
                           SELECT COUNT(DISTINCT username) as count
                           FROM chat_sessions
                           WHERE DATE(last_updated) = CURDATE()
                           """)
            stats["active_today"] = cursor.fetchone()['count']

            cursor.close()
        except Exception as e:
            print(f"获取数据库统计失败: {e}")

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")

# ============ 工具API ============
@app.post("/api/tools/entity-recognition")
async def tool_entity_recognition(query: str, user: Dict = Depends(get_current_user)):
    """实体识别工具"""
    try:
        entities = entity_recognition(query)
        return {
            "success": True,
            "query": query,
            "entities": entities
        }
    except Exception as e:
        print(f"实体识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"实体识别失败: {str(e)}")

@app.post("/api/tools/intent-recognition")
async def tool_intent_recognition(query: str, model_choice: str = None,
                                  user: Dict = Depends(get_current_user)):
    """意图识别工具"""
    if model_choice is None:
        model_choice = DEEPSEEK_MODEL
    try:
        intent_result = intent_recognition(query, model_choice)
        return {
            "success": True,
            "query": query,
            "intent_result": intent_result
        }
    except Exception as e:
        print(f"意图识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"意图识别失败: {str(e)}")

# ============ 应用生命周期事件 ============
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("=" * 50)
    print("术后管理系统API服务启动中...")
    print("=" * 50)

    # 加载模型
    load_models()

    # 连接数据库
    if db.connect():
        print("✅ 数据库连接成功")
    else:
        print("⚠️ 数据库连接失败，部分功能可能不可用")

    print(f"服务地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print(f"WebSocket: ws://localhost:8000/ws")
    print("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("正在关闭服务...")

    # 关闭数据库连接
    db.close()
    print("数据库连接已关闭")

    print("服务已关闭")

# ============ 错误处理 ============
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    print(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器内部错误: {str(exc)}"
        }
    )

# ============ 主程序入口 ============
if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True  # 开发时启用热重载
    )