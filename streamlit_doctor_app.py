import streamlit as st
import requests
import json
import pandas as pd

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="术后管理系统 - 医生端", page_icon="🩺")
st.title("🩺 术后管理系统 - 医生端")

if "username" not in st.session_state:
    st.session_state.username = ""
if "token" not in st.session_state:
    st.session_state.token = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


def auth_section():
    st.sidebar.header("医生认证")
    if not st.session_state.logged_in:
        auth_choice = st.sidebar.radio("选择操作", ["登录", "注册"])
        if auth_choice == "登录":
            username = st.sidebar.text_input("用户名", key="login_username")
            password = st.sidebar.text_input("密码", type="password", key="login_password")
            if st.sidebar.button("登录"):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/auth/login",
                        json={"username": username, "password": password}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if not data.get("is_admin", False):
                            st.sidebar.error("该账户不是医生，请使用医生账户登录。")
                            return
                        st.session_state.username = data["username"]
                        st.session_state.token = data["token"]
                        st.session_state.is_admin = True
                        st.session_state.logged_in = True
                        st.sidebar.success(f"欢迎回来, {st.session_state.username} (🩺 医生)!")
                        st.rerun()
                    else:
                        st.sidebar.error(f"登录失败: {response.json().get('detail', '未知错误')}")
                except requests.exceptions.ConnectionError:
                    st.sidebar.error("无法连接到后端服务，请确保后端已启动。")
                except Exception as e:
                    st.sidebar.error(f"发生错误: {e}")
        else:
            username = st.sidebar.text_input("用户名", key="register_username")
            password = st.sidebar.text_input("密码", type="password", key="register_password")
            confirm_password = st.sidebar.text_input("确认密码", type="password", key="register_confirm_password")
            st.sidebar.caption("注册即视为医生账户")
            if st.sidebar.button("注册"):
                try:
                    payload = {
                        "username": username, "password": password,
                        "confirm_password": confirm_password, "is_admin": True
                    }
                    response = requests.post(f"{API_BASE_URL}/auth/register", json=payload)
                    if response.status_code == 200:
                        st.sidebar.success("注册成功，请登录。")
                    else:
                        st.sidebar.error(f"注册失败: {response.json().get('detail', '未知错误')}")
                except requests.exceptions.ConnectionError:
                    st.sidebar.error("无法连接到后端服务，请确保后端已启动。")
                except Exception as e:
                    st.sidebar.error(f"发生错误: {e}")
    else:
        st.sidebar.success(f"已登录: {st.session_state.username} (🩺 医生)")
        if st.sidebar.button("退出登录"):
            for key in ["logged_in", "is_admin", "username", "token"]:
                st.session_state[key] = False if key in ("logged_in", "is_admin") else ""
            st.rerun()


def doctor_console():
    st.header("医生端管理")
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    col_main, col_chat = st.columns([8, 2])

    with col_main:
        tab_a, tab_b, tab_c, tab_d = st.tabs(["患者列表", "告警通知", "高风险记录", "异常打卡"])

    with tab_a:
        st.subheader("患者列表")
        try:
            response = requests.get(f"{API_BASE_URL}/doctor/patients", headers=headers)
            if response.status_code == 200:
                patients = response.json().get("patients", [])
                if patients:
                    st.dataframe(pd.DataFrame(patients), width='stretch')
                else:
                    st.info("暂无患者数据")
            else:
                st.error(response.json().get("detail", "获取患者列表失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    with tab_b:
        st.subheader("待处理告警")
        st.caption("高风险评估自动触发，需医生确认处理")
        try:
            alerts_response = requests.get(f"{API_BASE_URL}/doctor/alerts", headers=headers, params={"status": "pending"})
            if alerts_response.status_code == 200:
                alerts = alerts_response.json().get("alerts", [])
                if not alerts:
                    st.success("暂无待处理告警")
                else:
                    for alert in alerts:
                        name_text = alert.get("real_name") or alert.get("username")
                        with st.expander(f"{alert['created_at']} | {name_text} | {alert.get('source_type', '')}"):
                            st.write("患者用户名：", alert.get("username", ""))
                            st.markdown(f"**风险等级**：🛑 {alert.get('risk_level', '')}")
                            st.write("风险原因：")
                            st.write(alert.get("risk_reasons", ""))
                            st.write("系统建议：")
                            st.write(alert.get("advice", ""))
                            c1, _ = st.columns(2)
                            with c1:
                                if st.button("标记已处理", key=f"alert_process_{alert['id']}"):
                                    proc_resp = requests.post(
                                        f"{API_BASE_URL}/doctor/alerts/process",
                                        headers=headers,
                                        json={"alert_id": alert["id"]}
                                    )
                                    if proc_resp.status_code == 200:
                                        st.success("已标记处理")
                                        st.rerun()
                                    else:
                                        st.error("标记失败")
            else:
                st.error(alerts_response.json().get("detail", "获取告警失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

        st.divider()
        st.subheader("已处理告警")
        if st.button("查看已处理", key="show_processed"):
            try:
                processed_resp = requests.get(f"{API_BASE_URL}/doctor/alerts", headers=headers, params={"status": "processed"})
                if processed_resp.status_code == 200:
                    processed = processed_resp.json().get("alerts", [])
                    if processed:
                        st.dataframe(pd.DataFrame(processed), width='stretch')
                    else:
                        st.info("暂无已处理告警")
            except Exception as e:
                st.error(f"请求失败: {e}")

    with tab_c:
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
                            st.write("输入内容：")
                            st.write(item.get("input_text", ""))
                            st.write("风险原因：", item.get("risk_reasons", ""))
                            st.write("建议：", item.get("advice", ""))
                else:
                    st.success("当前暂无高风险评估记录")
            else:
                st.error(response.json().get("detail", "获取高风险记录失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    with tab_d:
        st.subheader("异常打卡记录")
        try:
            response = requests.get(f"{API_BASE_URL}/doctor/abnormal-checkins", headers=headers)
            if response.status_code == 200:
                records = response.json().get("records", [])
                if records:
                    for item in records:
                        name_text = item.get("real_name") or item.get("username")
                        with st.expander(f"{item['checkin_date']} | {name_text} | 异常打卡"):
                            st.write("症状：", item.get("symptoms", ""))
                            st.write("体温/血压/血糖/心率：",
                                     f"{item.get('temperature','')}/{item.get('blood_pressure','')}/{item.get('blood_sugar','')}/{item.get('heart_rate','')}")
                            st.write("异常原因：", item.get("abnormal_reason", ""))
                else:
                    st.success("当前暂无异常打卡记录")
            else:
                st.error(response.json().get("detail", "获取异常打卡失败"))
        except Exception as e:
            st.error(f"请求失败: {e}")

    with col_chat:
        st.subheader("💬 患者交互")
        query_username = st.text_input("输入患者用户名", key="doctor_chat_username")
        if not query_username.strip():
            st.info("输入患者用户名后开始对话")
            return

        st.caption("患者信息")
        try:
            detail_resp = requests.get(
                f"{API_BASE_URL}/doctor/patient-detail",
                headers=headers,
                params={"username": query_username}
            )
            if detail_resp.status_code == 200:
                data = detail_resp.json().get("data", {})
                profile = data.get("profile", {})
                latest = data.get("latest_assessment")
                if profile:
                    st.metric("姓名", profile.get("real_name") or "未填写")
                    st.metric("阶段", profile.get("health_stage") or "-")
                if latest:
                    risk = latest.get("risk_level", "未知")
                    if risk == "高风险":
                        st.error(f"风险：{risk}")
                    elif risk == "中风险":
                        st.warning(f"风险：{risk}")
                    else:
                        st.info(f"风险：{risk}")
        except Exception as e:
            st.error(f"请求失败: {e}")

        st.caption("消息记录")
        try:
            msg_resp = requests.get(
                f"{API_BASE_URL}/doctor/messages",
                headers=headers,
                params={"patient_username": query_username}
            )
            if msg_resp.status_code == 200:
                messages = msg_resp.json().get("messages", [])
                if messages:
                    for msg in messages[-20:]:
                        is_doctor = msg.get("doctor_username") != query_username or msg.get("doctor_username") == st.session_state.username
                        with st.chat_message("assistant" if is_doctor else "user"):
                            st.markdown(msg.get("content", ""))
                            st.caption(msg.get("created_at", "")[:19])
                else:
                    st.info("暂无消息记录")
        except Exception as e:
            st.error(f"获取消息失败: {e}")

        st.divider()
        with st.form(key="doctor_chat_form", clear_on_submit=True):
            msg_content = st.text_area("消息内容", height=80, placeholder="输入给患者的消息...")
            if st.form_submit_button("发送"):
                if not msg_content.strip():
                    st.warning("请输入消息内容")
                else:
                    try:
                        send_resp = requests.post(
                            f"{API_BASE_URL}/doctor/message",
                            headers=headers,
                            json={"patient_username": query_username, "content": msg_content.strip()}
                        )
                        if send_resp.status_code == 200:
                            st.success("消息已发送")
                            st.rerun()
                        else:
                            st.error(send_resp.json().get("detail", "发送失败"))
                    except Exception as e:
                        st.error(f"请求失败: {e}")


auth_section()
if st.session_state.logged_in:
    doctor_console()
else:
    st.info("请先在左侧边栏登录或注册医生账户。")
