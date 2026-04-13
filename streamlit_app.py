import streamlit as st
import requests
import json
import time

# FastAPI 后端地址
API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="术后管理系统", page_icon="⚕️")

st.title("⚕️ 智能术后管理系统")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "username" not in st.session_state:
    st.session_state.username = ""
if "token" not in st.session_state:
    st.session_state.token = ""
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 登录/注册界面
def auth_section():
    st.sidebar.header("用户认证")
    if not st.session_state.logged_in:
        auth_choice = st.sidebar.radio("选择操作", ["登录", "注册"])

        if auth_choice == "登录":
            username = st.sidebar.text_input("用户名", key="login_username")
            password = st.sidebar.text_input("密码", type="password", key="login_password")
            if st.sidebar.button("登录"):
                try:
                    response = requests.post(f"{API_BASE_URL}/auth/login", json={"username": username, "password": password})
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.username = data["username"]
                        st.session_state.token = data["token"]
                        st.session_state.logged_in = True
                        st.sidebar.success(f"欢迎回来, {st.session_state.username}!")
                        st.experimental_rerun()
                    else:
                        st.sidebar.error(f"登录失败: {response.json().get('detail', '未知错误')}")
                except requests.exceptions.ConnectionError:
                    st.sidebar.error("无法连接到后端服务，请确保后端已启动。")
                except Exception as e:
                    st.sidebar.error(f"发生错误: {e}")
        else: # 注册
            username = st.sidebar.text_input("用户名", key="register_username")
            password = st.sidebar.text_input("密码", type="password", key="register_password")
            confirm_password = st.sidebar.text_input("确认密码", type="password", key="register_confirm_password")
            if st.sidebar.button("注册"):
                try:
                    response = requests.post(f"{API_BASE_URL}/auth/register", json={"username": username, "password": password, "confirm_password": confirm_password})
                    if response.status_code == 200:
                        st.sidebar.success("注册成功，请登录。")
                    else:
                        st.sidebar.error(f"注册失败: {response.json().get('detail', '未知错误')}")
                except requests.exceptions.ConnectionError:
                    st.sidebar.error("无法连接到后端服务，请确保后端已启动。")
                except Exception as e:
                    st.sidebar.error(f"发生错误: {e}")
    else:
        st.sidebar.success(f"已登录: {st.session_state.username}")
        if st.sidebar.button("退出登录"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.token = ""
            st.session_state.session_id = None
            st.session_state.messages = []
            st.experimental_rerun()

# 聊天界面
def chat_section():
    st.header("与医疗助手对话")

    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "message": prompt,
            "model_choice": "deepseek-chat", # 可以从配置中读取或让用户选择
            "session_id": st.session_state.session_id,
            "stream": True
        }

        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                response = requests.post(f"{API_BASE_URL}/chat", headers=headers, json=payload, stream=True)
                
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=None): # chunk_size=None for line-by-line
                        if chunk:
                            try:
                                # Streamlit 期望每个 chunk 都是一个完整的 JSON 对象
                                # FastAPI 的 StreamingResponse 每次发送一个 JSON 对象后换行
                                for line in chunk.decode('utf-8').splitlines():
                                    if line.strip():
                                        data = json.loads(line)
                                        if data["type"] == "start":
                                            st.session_state.session_id = data["session_id"]
                                        elif data["type"] == "chunk":
                                            full_response += data["content"]
                                            message_placeholder.markdown(full_response + "▌") # 光标效果
                                        elif data["type"] == "complete":
                                            # 可以在这里处理 entities, intents 等信息
                                            pass
                                        elif data["type"] == "error":
                                            st.error(f"后端处理错误: {data['error']}")
                                            full_response += f"\n**错误:** {data['error']}"
                                            break # 停止接收更多 chunk
                            except json.JSONDecodeError:
                                # 有时 chunk 可能不是完整的 JSON，或者包含多个 JSON 对象
                                # 简单处理，如果不是完整 JSON 就跳过
                                pass
                    message_placeholder.markdown(full_response) # 移除光标
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                else:
                    error_msg = response.json().get('detail', '未知错误')
                    st.error(f"后端请求失败: {error_msg}")
                    st.session_state.messages.append({"role": "assistant", "content": f"抱歉，请求失败: {error_msg}"})
        except requests.exceptions.ConnectionError:
            st.error("无法连接到后端服务，请确保后端已启动。")
            st.session_state.messages.append({"role": "assistant", "content": "抱歉，无法连接到后端服务。"})
        except Exception as e:
            st.error(f"发生错误: {e}")
            st.session_state.messages.append({"role": "assistant", "content": f"抱歉，发生错误: {e}"})

# 主应用逻辑
auth_section()

if st.session_state.logged_in:
    chat_section()
else:
    st.info("请先在左侧边栏登录或注册。")
