import streamlit as st
import requests
import json
import time
import base64
from io import BytesIO
import pandas as pd

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
if "audio_data" not in st.session_state:
    st.session_state.audio_data = None
if "show_audio_input" not in st.session_state:
    st.session_state.show_audio_input = False

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
                        st.rerun()
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
            st.rerun()

# 聊天界面
def chat_section():
    st.header("与医疗助手对话")

    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 语音输入按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        prompt = st.chat_input("请输入您的问题...")
    with col2:
        if st.button("🎤 语音输入"):
            print("[DEBUG] 点击了语音输入按钮")
            st.session_state.show_audio_input = True
            st.rerun()
    
    # 语音输入组件
    if st.session_state.show_audio_input:
        print("[DEBUG] 显示音频输入组件")
        audio = st.sidebar.audio_input("录制语音", key="audio_input")
        print(f"[DEBUG] 音频对象: {audio}")
        
        if audio:
            print(f"[DEBUG] 音频文件类型: {type(audio)}")
            try:
                st.session_state.audio_data = audio
                print(f"[DEBUG] 音频数据已保存到会话状态")
                
                # 显示上传状态
                with st.spinner("正在处理语音..."):
                    # 上传音频到后端进行识别
                    audio_data = audio.getvalue()
                    print(f"[DEBUG] 音频数据大小: {len(audio_data)} bytes")
                    
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": ("audio.wav", audio_data, "audio/wav")}
                    print(f"[DEBUG] 准备发送请求到: {API_BASE_URL}/multimodal/speech/stt")
                    
                    try:
                        response = requests.post(f"{API_BASE_URL}/multimodal/speech/stt", headers=headers, files=files, timeout=30)
                        print(f"[DEBUG] 请求状态码: {response.status_code}")
                        print(f"[DEBUG] 请求响应: {response.text}")
                        
                        if response.status_code == 200:
                            result = response.json()
                            print(f"[DEBUG] 识别结果: {result}")
                            prompt = result.get("text", "")
                            answer = result.get("answer", "")
                            if prompt:
                                print(f"[DEBUG] 识别文本: {prompt}")
                                # 添加用户消息
                                st.session_state.messages.append({"role": "user", "content": prompt})
                                with st.chat_message("user"):
                                    st.markdown(prompt)
                                    st.audio(audio)
                                # 如果有回答，添加助手消息
                                if answer:
                                    print(f"[DEBUG] 回答内容: {answer}")
                                    st.session_state.messages.append({"role": "assistant", "content": answer})
                                    with st.chat_message("assistant"):
                                        st.markdown(answer)
                                # 重置状态
                                st.session_state.show_audio_input = False
                                st.session_state.audio_data = None
                                # 刷新页面以显示新消息
                                print("[DEBUG] 准备刷新页面")
                                st.rerun()
                            else:
                                print("[DEBUG] 识别结果为空")
                                st.error("语音识别结果为空，请重试")
                        else:
                            print(f"[DEBUG] 请求失败: {response.text}")
                            st.error(f"语音识别失败: {response.json().get('detail', '未知错误')}")
                    except requests.RequestException as e:
                        print(f"[DEBUG] 请求异常: {str(e)}")
                        st.error(f"语音识别请求失败: {e}")
                
            except Exception as e:
                print(f"[DEBUG] 音频处理异常: {str(e)}")
                st.error(f"音频处理失败: {e}")
        
        # 取消按钮
        if st.sidebar.button("取消语音输入"):
            print("[DEBUG] 取消语音输入")
            st.session_state.show_audio_input = False
            st.session_state.audio_data = None
            st.rerun()

    # 文本输入处理
    if prompt:
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
                    
                    # 语音播放按钮
                    if st.button("🔊 语音播放"):
                        # 调用语音合成接口
                        try:
                            tts_response = requests.post(f"{API_BASE_URL}/multimodal/speech/tts", 
                                                       headers=headers, 
                                                       json={"text": full_response})
                            if tts_response.status_code == 200:
                                tts_result = tts_response.json()
                                if tts_result.get("audio"):
                                    # 处理音频数据
                                    st.audio(tts_result["audio"])
                                else:
                                    st.info("语音合成功能尚未完全实现")
                            else:
                                st.error(f"语音合成失败: {tts_response.json().get('detail', '未知错误')}")
                        except Exception as e:
                            st.error(f"语音合成请求失败: {e}")
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

# 图片上传和OCR功能
def image_ocr_section():
    st.header("病例图片识别")
    
    # 文件上传组件
    uploaded_file = st.file_uploader("上传病例图片", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        # 显示上传的图片
        st.image(uploaded_file, caption="上传的图片", width=800)
        
        # 处理图片上传
        if st.button("开始识别"):
            with st.spinner("正在识别中..."):
                try:
                    # 准备文件数据
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    data = {"auto_answer": True}
                    
                    # 发送请求到后端
                    response = requests.post(f"{API_BASE_URL}/multimodal/image/ocr", headers=headers, files=files, data=data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            # 显示OCR结果
                            st.subheader("OCR识别结果")
                            ocr_text = result.get("ocr_text", "")
                            st.text_area("识别文本", ocr_text, height=200)
                            
                            # 显示AI分析建议
                            answer = result.get("answer", "")
                            if answer:
                                st.subheader("AI分析建议")
                                st.markdown(answer)
                            
                            # 显示结构化数据
                            structured = result.get("structured", {})
                            if structured:
                                st.subheader("结构化数据")
                                st.json(structured)
                        else:
                            st.error("识别失败")
                    else:
                        st.error(f"请求失败: {response.json().get('detail', '未知错误')}")
                except requests.exceptions.ConnectionError:
                    st.error("无法连接到后端服务，请确保后端已启动。")
                except Exception as e:
                    st.error(f"发生错误: {e}")

# 健康评估结果显示
def show_health_result(result):
    st.subheader("评估结果")

    risk_level = result.get("risk_level", "未知")
    if risk_level == "高风险":
        st.error(f"风险等级：{risk_level}")
    elif risk_level == "中风险":
        st.warning(f"风险等级：{risk_level}")
    else:
        st.info(f"风险等级：{risk_level}")

    st.write("风险原因：")
    for reason in result.get("risk_reasons", []):
        st.write(f"- {reason}")

    st.write("建议尽快线下就医：", "是" if result.get("need_hospital") else "否")

    st.subheader("健康建议")
    st.markdown(result.get("advice", ""))

# 健康评估功能
def health_assessment_section():
    st.header("健康评估中心")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    mode = st.radio("选择输入方式", ["文字输入", "语音上传", "图片/PDF上传"], horizontal=True)

    if mode == "文字输入":
        text = st.text_area("请输入健康问题、症状描述、检查结果或报告摘要", height=180)
        if st.button("开始文字评估"):
            if not text.strip():
                st.warning("请输入内容")
                return

            data = {
                "input_text": text,
                "session_id": st.session_state.session_id or ""
            }

            response = requests.post(
                f"{API_BASE_URL}/health/assess/text",
                headers=headers,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                show_health_result(result)
            else:
                st.error(response.json().get("detail", "评估失败"))

    elif mode == "语音上传":
        audio_file = st.file_uploader("上传语音文件", type=["wav", "mp3", "m4a"], key="health_audio")
        if audio_file and st.button("开始语音评估"):
            files = {"file": (audio_file.name, audio_file.getvalue(), audio_file.type)}
            data = {"session_id": st.session_state.session_id or ""}

            response = requests.post(
                f"{API_BASE_URL}/health/assess/speech",
                headers=headers,
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                show_health_result(result)
            else:
                st.error(response.json().get("detail", "语音评估失败"))

    elif mode == "图片/PDF上传":
        uploaded = st.file_uploader("上传检查单、病例图片或 PDF", type=["png", "jpg", "jpeg", "pdf"], key="health_image")
        if uploaded:
            if uploaded.type.startswith("image/"):
                st.image(uploaded, caption="上传内容", width=700)

            if st.button("开始图片评估"):
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                data = {"session_id": st.session_state.session_id or ""}

                response = requests.post(
                    f"{API_BASE_URL}/health/assess/image",
                    headers=headers,
                    files=files,
                    data=data
                )

                if response.status_code == 200:
                    result = response.json()
                    show_health_result(result)

                    if result.get("ocr_structured"):
                        st.subheader("OCR结构化结果")
                        st.json(result["ocr_structured"])
                else:
                    st.error(response.json().get("detail", "图片评估失败"))

    st.divider()
    st.subheader("历史评估记录")

    if st.button("刷新历史记录"):
        response = requests.get(f"{API_BASE_URL}/health/assess/history", headers=headers)
        if response.status_code == 200:
            records = response.json().get("records", [])
            if not records:
                st.info("暂无评估记录")
            else:
                for item in records:
                    with st.expander(f"{item['created_at']} | {item['risk_level']} | {item['source_type']}"):
                        st.write("输入内容：")
                        st.write(item["input_text"])
                        st.write("风险原因：")
                        st.write(item["risk_reasons"])
                        st.write("建议：")
                        st.write(item["advice"])
                        st.write("建议线下就医：", "是" if item["need_hospital"] else "否")
        else:
            st.error(response.json().get("detail", "获取历史记录失败"))

# 健康档案功能
def profile_section():
    st.header("健康档案")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    try:
        response = requests.get(f"{API_BASE_URL}/profile/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            profile = data.get("profile") or {}
            latest_assessment = data.get("latest_assessment")
        else:
            st.error("获取健康档案失败")
            return
    except Exception as e:
        st.error(f"请求失败: {e}")
        return

    with st.form("profile_form"):
        real_name = st.text_input("姓名", value=profile.get("real_name", ""))
        gender = st.selectbox(
            "性别",
            ["", "男", "女", "其他"],
            index=["", "男", "女", "其他"].index(profile.get("gender", "")) if profile.get("gender", "") in ["", "男", "女", "其他"] else 0
        )
        age = st.number_input("年龄", min_value=0, max_value=120, value=int(profile["age"]) if profile.get("age") is not None else 0)
        phone = st.text_input("手机号", value=profile.get("phone", ""))
        height = st.number_input("身高(cm)", min_value=0.0, max_value=250.0, value=float(profile["height"]) if profile.get("height") is not None else 0.0)
        weight = st.number_input("体重(kg)", min_value=0.0, max_value=300.0, value=float(profile["weight"]) if profile.get("weight") is not None else 0.0)
        blood_type = st.text_input("血型", value=profile.get("blood_type", ""))
        health_stage = st.selectbox(
            "当前健康阶段",
            ["就诊前", "治疗中", "康复期", "长期管理"],
            index=["就诊前", "治疗中", "康复期", "长期管理"].index(profile.get("health_stage", "长期管理")) if profile.get("health_stage", "长期管理") in ["就诊前", "治疗中", "康复期", "长期管理"] else 3
        )
        medical_history = st.text_area("既往病史", value=profile.get("medical_history", ""), height=120)
        allergy_history = st.text_area("过敏史", value=profile.get("allergy_history", ""), height=100)
        current_medications = st.text_area("当前用药", value=profile.get("current_medications", ""), height=100)
        emergency_contact = st.text_input("紧急联系人", value=profile.get("emergency_contact", ""))
        emergency_phone = st.text_input("紧急联系电话", value=profile.get("emergency_phone", ""))

        submitted = st.form_submit_button("保存健康档案")

    if submitted:
        payload = {
            "real_name": real_name,
            "gender": gender,
            "age": int(age) if age != 0 else None,
            "phone": phone,
            "height": float(height) if height != 0 else None,
            "weight": float(weight) if weight != 0 else None,
            "blood_type": blood_type,
            "medical_history": medical_history,
            "allergy_history": allergy_history,
            "current_medications": current_medications,
            "emergency_contact": emergency_contact,
            "emergency_phone": emergency_phone,
            "health_stage": health_stage
        }

        try:
            save_resp = requests.post(f"{API_BASE_URL}/profile/me", headers=headers, json=payload)
            if save_resp.status_code == 200:
                st.success("健康档案保存成功")
                st.rerun()
            else:
                st.error(save_resp.json().get("detail", "保存失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    st.divider()
    st.subheader("最近一次健康评估")

    if latest_assessment:
        st.write("评估时间：", latest_assessment.get("created_at", ""))
        risk_level = latest_assessment.get("risk_level", "未知")
        if risk_level == "高风险":
            st.error(f"风险等级：{risk_level}")
        elif risk_level == "中风险":
            st.warning(f"风险等级：{risk_level}")
        else:
            st.info(f"风险等级：{risk_level}")

        st.write("输入来源：", latest_assessment.get("source_type", ""))
        st.write("输入内容：")
        st.write(latest_assessment.get("input_text", ""))

        st.write("风险原因：")
        st.write(latest_assessment.get("risk_reasons", ""))

        st.write("建议：")
        st.write(latest_assessment.get("advice", ""))

        st.write("建议线下就医：", "是" if latest_assessment.get("need_hospital") else "否")
    else:
        st.info("暂无健康评估记录")

# 每日健康打卡功能
from datetime import date, time

def daily_checkin_section():
    st.header("每日健康打卡")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    with st.form("daily_checkin_form"):
        checkin_date = st.date_input("打卡日期", value=date.today())
        symptoms = st.text_area("今日症状", placeholder="如：轻微头晕、食欲一般、无发热", height=100)
        temperature = st.number_input("体温（℃）", min_value=0.0, max_value=45.0, value=0.0, step=0.1)
        blood_pressure = st.text_input("血压（格式：120/80）")
        blood_sugar = st.number_input("血糖（mmol/L）", min_value=0.0, max_value=50.0, value=0.0, step=0.1)
        heart_rate = st.number_input("心率（次/分）", min_value=0, max_value=250, value=0)
        sleep_status = st.selectbox("睡眠情况", ["", "良好", "一般", "较差"])
        diet_status = st.selectbox("饮食情况", ["", "正常", "一般", "较差"])
        exercise_status = st.selectbox("运动情况", ["", "无", "轻度活动", "正常活动", "较多运动"])
        medication_taken = st.checkbox("今日已按时用药")
        note = st.text_area("备注", height=80)

        submitted = st.form_submit_button("提交今日打卡")

    if submitted:
        payload = {
            "checkin_date": str(checkin_date),
            "symptoms": symptoms,
            "temperature": None if temperature == 0.0 else float(temperature),
            "blood_pressure": blood_pressure,
            "blood_sugar": None if blood_sugar == 0.0 else float(blood_sugar),
            "heart_rate": None if heart_rate == 0 else int(heart_rate),
            "sleep_status": sleep_status,
            "diet_status": diet_status,
            "exercise_status": exercise_status,
            "medication_taken": medication_taken,
            "note": note
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/checkin/daily",
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                result = response.json()
                st.success(result.get("message", "打卡成功"))

                record = result.get("record", {})
                if record:
                    if record.get("abnormal_flag"):
                        st.warning(f"系统提示：{record.get('abnormal_reason', '')}")
                    else:
                        st.info(f"系统提示：{record.get('abnormal_reason', '')}")
            else:
                st.error(response.json().get("detail", "打卡失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    st.divider()
    st.subheader("最近 30 天打卡记录")

    if st.button("刷新打卡记录"):
        try:
            response = requests.get(f"{API_BASE_URL}/checkin/daily", headers=headers)
            if response.status_code == 200:
                records = response.json().get("records", [])
                if not records:
                    st.info("暂无打卡记录")
                else:
                    for item in records:
                        title = f"{item['checkin_date']} | {'异常' if item['abnormal_flag'] else '正常'}"
                        with st.expander(title):
                            st.write("症状：", item.get("symptoms", ""))
                            st.write("体温：", item.get("temperature", ""))
                            st.write("血压：", item.get("blood_pressure", ""))
                            st.write("血糖：", item.get("blood_sugar", ""))
                            st.write("心率：", item.get("heart_rate", ""))
                            st.write("睡眠：", item.get("sleep_status", ""))
                            st.write("饮食：", item.get("diet_status", ""))
                            st.write("运动：", item.get("exercise_status", ""))
                            st.write("按时用药：", "是" if item.get("medication_taken") else "否")
                            st.write("备注：", item.get("note", ""))
                            st.write("系统判断：", item.get("abnormal_reason", ""))
            else:
                st.error(response.json().get("detail", "获取打卡记录失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

# 趋势分析与健康概览
def overview_section():
    st.header("趋势分析 / 健康概览")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    days = st.selectbox("选择统计周期", [7, 14, 30], index=0)

    try:
        response = requests.get(
            f"{API_BASE_URL}/overview/dashboard",
            headers=headers,
            params={"days": days}
        )
    except Exception as e:
        st.error(f"请求失败: {e}")
        return

    if response.status_code != 200:
        st.error(response.json().get("detail", "获取健康概览失败"))
        return

    result = response.json()
    data = result.get("data", {})
    overview = data.get("overview", {})
    trend = data.get("trend", {})
    abnormal_records = data.get("abnormal_records", [])
    latest_assessment = data.get("latest_assessment")

    # 1. 概览卡片
    st.subheader("个人健康概览")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("姓名", overview.get("real_name") or "未填写")
    col2.metric("健康阶段", overview.get("health_stage") or "未设置")
    col3.metric("最近风险等级", overview.get("latest_risk_level") or "暂无")
    col4.metric("近7/14/30天异常次数", overview.get("abnormal_count", 0))

    col5, col6, col7 = st.columns(3)
    col5.metric("平均体温", overview.get("avg_temperature") if overview.get("avg_temperature") is not None else "暂无")
    col6.metric("平均心率", overview.get("avg_heart_rate") if overview.get("avg_heart_rate") is not None else "暂无")
    col7.metric("平均血糖", overview.get("avg_blood_sugar") if overview.get("avg_blood_sugar") is not None else "暂无")

    # 2. 最近一次健康评估
    st.divider()
    st.subheader("最近一次健康评估")
    if latest_assessment:
        risk_level = latest_assessment.get("risk_level", "未知")
        if risk_level == "高风险":
            st.error(f"风险等级：{risk_level}")
        elif risk_level == "中风险":
            st.warning(f"风险等级：{risk_level}")
        else:
            st.info(f"风险等级：{risk_level}")

        st.write("评估时间：", latest_assessment.get("created_at", ""))
        st.write("输入来源：", latest_assessment.get("source_type", ""))
        st.write("输入内容：")
        st.write(latest_assessment.get("input_text", ""))
    else:
        st.info("暂无健康评估记录")

    # 3. 趋势图
    st.divider()
    st.subheader("健康趋势图")

    dates = trend.get("dates", [])
    temperature = trend.get("temperature", [])
    blood_sugar = trend.get("blood_sugar", [])
    heart_rate = trend.get("heart_rate", [])

    if dates:
        df = pd.DataFrame({
            "日期": dates,
            "体温": temperature,
            "血糖": blood_sugar,
            "心率": heart_rate
        }).set_index("日期")

        st.write("体温趋势")
        st.line_chart(df[["体温"]], height=250)

        st.write("血糖趋势")
        st.line_chart(df[["血糖"]], height=250)

        st.write("心率趋势")
        st.line_chart(df[["心率"]], height=250)
    else:
        st.info("暂无打卡数据，无法生成趋势图")

    # 4. 异常记录
    st.divider()
    st.subheader("最近异常记录")

    if abnormal_records:
        for item in abnormal_records:
            with st.expander(f"{item['date']} | 异常记录"):
                st.write("异常原因：", item.get("reason", ""))
                st.write("相关症状：", item.get("symptoms", ""))
    else:
        st.success("最近没有异常记录")

def reminder_center_section():
    st.header("提醒中心")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    st.subheader("新建提醒")
    with st.form("reminder_form"):
        reminder_type = st.selectbox("提醒类型", ["用药提醒", "复诊提醒", "打卡提醒", "检查提醒", "其他"])
        title = st.text_input("提醒标题")
        description = st.text_area("提醒说明", height=100)
        reminder_date = st.date_input("提醒日期", value=date.today())
        reminder_time = st.time_input("提醒时间", value=time(9, 0))
        create_submitted = st.form_submit_button("创建提醒")

    if create_submitted:
        if not title.strip():
            st.warning("请输入提醒标题")
        else:
            payload = {
                "reminder_type": reminder_type,
                "title": title,
                "description": description,
                "reminder_date": str(reminder_date),
                "reminder_time": reminder_time.strftime("%H:%M:%S")
            }

            try:
                response = requests.post(
                    f"{API_BASE_URL}/reminder/",
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    st.success("提醒创建成功")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "创建提醒失败"))
            except Exception as e:
                st.error(f"请求失败: {e}")

    st.divider()
    st.subheader("我的提醒")

    try:
        response = requests.get(f"{API_BASE_URL}/reminder/", headers=headers)
        if response.status_code != 200:
            st.error(response.json().get("detail", "获取提醒失败"))
            return
    except Exception as e:
        st.error(f"请求失败: {e}")
        return

    result = response.json()
    reminders = result.get("reminders", [])
    today_stats = result.get("today_stats", {})

    col1, col2 = st.columns(2)
    col1.metric("今日待完成提醒", today_stats.get("pending_count", 0))
    col2.metric("今日已完成提醒", today_stats.get("completed_count", 0))

    if not reminders:
        st.info("暂无提醒")
        return

    for item in reminders:
        status_text = "已完成" if item["status"] == "completed" else "待完成"
        with st.expander(f"{item['reminder_date']} {item.get('reminder_time') or ''} | {item['title']} | {status_text}"):
            st.write("提醒类型：", item.get("reminder_type", ""))
            st.write("提醒说明：", item.get("description", ""))
            st.write("状态：", status_text)

            c1, c2 = st.columns(2)

            with c1:
                if item["status"] == "pending":
                    if st.button("标记完成", key=f"complete_{item['id']}"):
                        payload = {
                            "reminder_id": item["id"],
                            "status": "completed"
                        }
                        resp = requests.post(
                            f"{API_BASE_URL}/reminder/status",
                            headers=headers,
                            json=payload
                        )
                        if resp.status_code == 200:
                            st.success("已标记完成")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "更新失败"))
                else:
                    if st.button("恢复待完成", key=f"pending_{item['id']}"):
                        payload = {
                            "reminder_id": item["id"],
                            "status": "pending"
                        }
                        resp = requests.post(
                            f"{API_BASE_URL}/reminder/status",
                            headers=headers,
                            json=payload
                        )
                        if resp.status_code == 200:
                            st.success("已恢复为待完成")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "更新失败"))

            with c2:
                if st.button("删除提醒", key=f"delete_{item['id']}"):
                    resp = requests.delete(
                        f"{API_BASE_URL}/reminder/{item['id']}",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        st.success("提醒已删除")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "删除失败"))

# 医生端管理（最小版）
def doctor_console_section():
    st.header("医生端管理（最小版）")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    tab_a, tab_b, tab_c, tab_d = st.tabs(["患者列表", "高风险记录", "异常打卡", "患者详情"])

    # 1. 患者列表
    with tab_a:
        st.subheader("患者列表")
        try:
            response = requests.get(f"{API_BASE_URL}/doctor/patients", headers=headers)
            if response.status_code == 200:
                patients = response.json().get("patients", [])
                if patients:
                    df = pd.DataFrame(patients)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("暂无患者数据")
            else:
                st.error(response.json().get("detail", "获取患者列表失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    # 2. 高风险记录
    with tab_b:
        st.subheader("高风险健康评估记录")
        try:
            response = requests.get(f"{API_BASE_URL}/doctor/high-risk", headers=headers)
            if response.status_code == 200:
                records = response.json().get("records", [])
                if records:
                    for item in records:
                        name_text = item.get("real_name") or item.get("username")
                        with st.expander(f"{item['created_at']} | {name_text} | 高风险"):
                            st.write("患者用户名：", item.get("username", ""))
                            st.write("姓名：", item.get("real_name", ""))
                            st.write("输入来源：", item.get("source_type", ""))
                            st.write("输入内容：")
                            st.write(item.get("input_text", ""))
                            st.write("风险原因：")
                            st.write(item.get("risk_reasons", ""))
                            st.write("建议：")
                            st.write(item.get("advice", ""))
                            st.write("建议线下就医：", "是" if item.get("need_hospital") else "否")
                else:
                    st.success("当前暂无高风险评估记录")
            else:
                st.error(response.json().get("detail", "获取高风险记录失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    # 3. 异常打卡
    with tab_c:
        st.subheader("异常打卡记录")
        try:
            response = requests.get(f"{API_BASE_URL}/doctor/abnormal-checkins", headers=headers)
            if response.status_code == 200:
                records = response.json().get("records", [])
                if records:
                    for item in records:
                        name_text = item.get("real_name") or item.get("username")
                        with st.expander(f"{item['checkin_date']} | {name_text} | 异常打卡"):
                            st.write("患者用户名：", item.get("username", ""))
                            st.write("姓名：", item.get("real_name", ""))
                            st.write("症状：", item.get("symptoms", ""))
                            st.write("体温：", item.get("temperature", ""))
                            st.write("血压：", item.get("blood_pressure", ""))
                            st.write("血糖：", item.get("blood_sugar", ""))
                            st.write("心率：", item.get("heart_rate", ""))
                            st.write("异常原因：", item.get("abnormal_reason", ""))
                else:
                    st.success("当前暂无异常打卡记录")
            else:
                st.error(response.json().get("detail", "获取异常打卡失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    # 4. 患者详情
    with tab_d:
        st.subheader("患者详情查看")
        query_username = st.text_input("请输入患者用户名", key="doctor_query_username")

        if st.button("查询患者详情", key="doctor_query_btn"):
            if not query_username.strip():
                st.warning("请输入患者用户名")
            else:
                try:
                    response = requests.get(
                        f"{API_BASE_URL}/doctor/patient-detail",
                        headers=headers,
                        params={"username": query_username}
                    )
                    if response.status_code == 200:
                        data = response.json().get("data", {})
                        profile = data.get("profile")
                        latest_assessment = data.get("latest_assessment")
                        recent_checkins = data.get("recent_checkins", [])
                        recent_reminders = data.get("recent_reminders", [])

                        st.subheader("健康档案")
                        if profile:
                            st.json(profile)
                        else:
                            st.info("该患者暂无健康档案")

                        st.subheader("最近一次健康评估")
                        if latest_assessment:
                            risk_level = latest_assessment.get("risk_level", "未知")
                            if risk_level == "高风险":
                                st.error(f"风险等级：{risk_level}")
                            elif risk_level == "中风险":
                                st.warning(f"风险等级：{risk_level}")
                            else:
                                st.info(f"风险等级：{risk_level}")

                            st.write("评估时间：", latest_assessment.get("created_at", ""))
                            st.write("输入来源：", latest_assessment.get("source_type", ""))
                            st.write("输入内容：")
                            st.write(latest_assessment.get("input_text", ""))
                            st.write("风险原因：")
                            st.write(latest_assessment.get("risk_reasons", ""))
                        else:
                            st.info("该患者暂无健康评估记录")

                        st.subheader("最近 7 条打卡记录")
                        if recent_checkins:
                            checkin_df = pd.DataFrame(recent_checkins)
                            st.dataframe(checkin_df, use_container_width=True)
                        else:
                            st.info("该患者暂无打卡记录")

                        st.subheader("最近提醒")
                        if recent_reminders:
                            reminder_df = pd.DataFrame(recent_reminders)
                            st.dataframe(reminder_df, use_container_width=True)
                        else:
                            st.info("该患者暂无提醒记录")
                    else:
                        st.error(response.json().get("detail", "查询患者详情失败"))
                except Exception as e:
                    st.error(f"请求失败: {e}")

# 主应用逻辑
auth_section()

if st.session_state.logged_in:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "与医疗助手对话",
        "病例图片识别",
        "健康评估中心",
        "健康档案",
        "每日健康打卡",
        "趋势分析/健康概览",
        "提醒中心",
        "医生端管理"
    ])

    with tab1:
        chat_section()

    with tab2:
        image_ocr_section()

    with tab3:
        health_assessment_section()

    with tab4:
        profile_section()

    with tab5:
        daily_checkin_section()

    with tab6:
        overview_section()

    with tab7:
        reminder_center_section()

    with tab8:
        doctor_console_section()
else:
    st.info("请先在左侧边栏登录或注册。")
