"""
streamlit_app.py — Streamlit Frontend for Smart PE recommendation system
Run: streamlit run app.py --server.port 8501
"""
import streamlit as st
from utils.api import api_request
from views.student import render_dashboard, render_fatigue, render_plan, render_feedback
from views.teacher import render_students, render_model
from views.chatbot import render_chatbot

st.set_page_config(
    page_title="Smart PE — ИИ-Тренер",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def login_page():
    st.title("🏋️ Smart PE — ИИ-Персональный Тренер")
    st.markdown("### Тренируйся с умом — прогрессируй с ИИ")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔐 Вход", "📝 Регистрация"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="student1@smartpe.edu")
                password = st.text_input("Пароль", type="password", placeholder="student123")
                submitted = st.form_submit_button("Войти", use_container_width=True)
                if submitted:
                    resp = api_request("POST", "/auth/login", json={"email": email, "password": password})
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.role = data["role"]
                        st.session_state.student_id = data.get("student_id")
                        st.session_state.email = email
                        st.success("✅ Успешный вход!")
                        st.rerun()
                    else:
                        st.error(f"❌ {resp.json().get('detail', 'Ошибка входа')}")

        with tab_register:
            with st.form("register_form"):
                r_email = st.text_input("Email")
                r_password = st.text_input("Пароль", type="password")
                r_role = st.selectbox("Роль", ["student", "teacher"])
                r_student_id = None
                if r_role == "student":
                    r_student_id = st.number_input("Student ID (из БД)", min_value=1, step=1)
                submitted = st.form_submit_button("Зарегистрироваться", use_container_width=True)
                if submitted:
                    payload = {"email": r_email, "password": r_password, "role": r_role}
                    if r_student_id:
                        payload["student_id"] = int(r_student_id)
                    resp = api_request("POST", "/auth/register", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.role = data["role"]
                        st.session_state.student_id = data.get("student_id")
                        st.session_state.email = r_email
                        st.success("✅ Регистрация успешна!")
                        st.rerun()
                    else:
                        st.error(f"❌ {resp.json().get('detail', 'Ошибка')}")

    st.markdown("---")
    st.info("💡 **Демо-аккаунты:**\n- Студент: `student1@smartpe.edu` / `student123`\n- Преподаватель: `teacher1@smartpe.edu` / `teacher123`")

def main():
    if "token" not in st.session_state:
        login_page()
        return

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.email}")
        st.markdown(f"**Роль:** {st.session_state.role}")
        if st.session_state.role == "student":
            st.markdown(f"**Student ID:** {st.session_state.student_id}")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown("---")
        st.markdown("*API: http://localhost:8000*")

    # Pages routing
    if st.session_state.role == "student":
        pages = [
            st.Page(render_dashboard, title="🏠 Профиль", icon="🏠"),
            st.Page(render_fatigue, title="💪 Мышцы", icon="💪"),
            st.Page(render_plan, title="📅 Планы", icon="📅"),
            st.Page(render_feedback, title="💬 Обратная связь", icon="💬"),
            st.Page(render_chatbot, title="🤖 AI Coach", icon="🤖"),
        ]
    else:
        pages = [
            st.Page(render_students, title="👥 Студенты", icon="👥"),
            st.Page(render_model, title="🤖 Модель", icon="🤖"),
            st.Page(render_chatbot, title="🤖 AI Coach", icon="🤖"),
        ]

    pg = st.navigation(pages)
    pg.run()

if __name__ == "__main__":
    main()