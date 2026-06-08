"""
Smart PE — Streamlit Frontend
Run: streamlit run streamlit_app.py --server.port 8501
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000"
st.set_page_config(
    page_title="Smart PE — ИИ-Тренер",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API Helper ──────────────────────────────────────────────────────────────
def api_request(method, path, **kwargs):
    """Make authenticated request to backend."""
    url = f"{API_URL}{path}"
    headers = kwargs.pop("headers", {})
    if "token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        resp = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        if resp.status_code == 401:
            st.session_state.clear()
            st.error("🔒 Сессия истекла. Войдите снова.")
            st.rerun()
        return resp
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Не удалось подключиться к API по адресу {API_URL}. Убедитесь, что backend запущен.")
        st.stop()

# ── Login Page ──────────────────────────────────────────────────────────────
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

# ── Student Pages ───────────────────────────────────────────────────────────
def student_dashboard():
    st.title("👋 Мой профиль")
    sid = st.session_state.student_id
    resp = api_request("GET", f"/students/{sid}")
    if resp.status_code != 200:
        st.error("Не удалось загрузить профиль"); return
    p = resp.json()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 Возраст", f"{p['age']} лет")
    c2.metric("⚕️ Мед. группа", p["medical_group"])
    c3.metric("📏 ИМТ", f"{p['biometrics']['bmi']:.1f}")
    c4.metric("🎯 Уровень", 
              f"{(p['assessment_scores']['strength']+p['assessment_scores']['endurance']+p['assessment_scores']['flexibility'])/3:.1f}/4")

    st.markdown("### 🏃 Кардио-выносливость")
    fig_cooper = go.Figure()
    fig_cooper.add_trace(go.Indicator(
        mode="gauge+number",
        value=p["fitness_metrics"]["cooper_meters"],
        title={"text": "Тест Купера (метры)"},
        gauge={
            "axis": {"range": [800, 3500]},
            "bar": {"color": "#4CAF50"},
            "steps": [
                {"range": [800, 2000], "color": "#ffcdd2"},
                {"range": [2000, 2400], "color": "#fff9c4"},
                {"range": [2400, 2800], "color": "#c8e6c9"},
                {"range": [2800, 3500], "color": "#a5d6a7"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 2800
            }
        }
    ))
    fig_cooper.update_layout(height=250)
    st.plotly_chart(fig_cooper, use_container_width=True)

    st.markdown("### 💪 Силовые показатели и гибкость")
    metrics = p["fitness_metrics"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Отжимания", "Подтягивания", "Пресс", "Гибкость (см)", "Прыжок (см)"],
        y=[metrics["push_ups"], metrics["pull_ups"], metrics["sit_ups"],
           metrics["flexibility"], metrics["jump_forward"]],
        marker_color=["#2196F3", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"],
        text=[metrics["push_ups"], metrics["pull_ups"], metrics["sit_ups"],
              f"{metrics['flexibility']:.1f}", metrics["jump_forward"]],
        textposition="auto"
    ))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    if p["active_injuries"]:
        st.markdown("### ⚠️ Активные травмы")
        for inj in p["active_injuries"]:
            st.warning(f"**{inj['type']}** ({inj['region']}) — до {inj['recovery_date']}")

def student_fatigue():
    st.title("💪 Состояние мышц")
    sid = st.session_state.student_id
    resp = api_request("GET", f"/students/{sid}/muscle-fatigue")
    if resp.status_code != 200:
        st.error("Ошибка загрузки"); return
    data = resp.json()
    if not data["active_fatigue"]:
        st.success("🎉 Все мышцы восстановлены! Можно тренироваться.")
        return

    df = pd.DataFrame(data["active_fatigue"])
    st.markdown(f"**{len(df)} мышечных групп** ещё восстанавливаются")
    fig = px.bar(df, x="muscle", y="recovery_left_h",
                 color="recovery_pct", color_continuous_scale="RdYlGn_r",
                 labels={"recovery_left_h": "Часов до восстановления", "muscle": "Мышца", "recovery_pct": "Восстановлено %"},
                 title="⏳ Оставшееся время восстановления")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    for _, row in df.iterrows():
        st.progress(row["recovery_pct"]/100, text=f"**{row['muscle']}** — {row['recovery_pct']:.0f}% восстановлено ({row['recovery_left_h']}ч осталось)")

def student_plan():
    st.title("📅 Мои планы тренировок")
    sid = st.session_state.student_id

    if st.button("✨ Сгенерировать новый план на неделю", type="primary", use_container_width=True):
        with st.spinner("🤖 ИИ подбирает упражнения под ваш профиль..."):
            resp = api_request("POST", "/plans/generate", json={"student_id": sid, "save_to_db": True})
            if resp.status_code == 200:
                st.success("✅ План сгенерирован и сохранён!")
                st.rerun()
            else:
                st.error(f"❌ {resp.json().get('detail')}")

    st.markdown("---")
    resp = api_request("GET", f"/plans/{sid}/history?limit=5")
    if resp.status_code != 200:
        st.error("Ошибка"); return
    plans = resp.json().get("plans", [])
    if not plans:
        st.info("📭 У вас пока нет планов. Сгенерируйте первый!")
        return

    for plan in plans:
        with st.expander(f"📋 План от {plan['date']} — {plan['status']}", expanded=(plan == plans[0])):
            ex_resp = api_request("GET", f"/plans/{plan['plan_id']}/exercises")
            if ex_resp.status_code != 200:
                continue
            exercises = ex_resp.json()["exercises"]
            for day in ["MONDAY", "WEDNESDAY", "FRIDAY"]:
                day_exs = [e for e in exercises if e["day_of_week"] == day]
                if not day_exs:
                    continue
                st.markdown(f"**🗓️ {day}**")
                for ex in day_exs:
                    status_emoji = {"COMPLETED": "✅", "SKIPPED": "⏭️", "SCHEDULED": "⏰", "DISCARDED": "❌"}.get(ex["status"], "❔")
                    slot_emoji = {"warmup": "🔥", "main": "💪", "cooldown": "🧘"}.get(ex["slot_type"], "")
                    st.markdown(f"{status_emoji} {slot_emoji} **{ex['exercise_name']}** — {ex['recommended_sets']}×{ex['recommended_reps']} "
                                f"*({ex['slot_type']}, score: {ex['predicted_score']:.2f})*")

            if st.button(f"🧠 Почему ИИ выбрал этот план?", key=f"explain_{plan['plan_id']}"):
                with st.spinner("Генерирую объяснение..."):
                    exp_resp = api_request("GET", f"/explain/plan/{sid}/ru")
                    if exp_resp.status_code == 200:
                        st.markdown("### 🧠 Объяснение ИИ")
                        st.code(exp_resp.json()["explanation"], language=None)
                    else:
                        st.error("Не удалось получить объяснение")

def student_feedback():
    st.title("💬 Обратная связь")
    st.markdown("Отметьте, как прошла последняя тренировка — это поможет ИИ улучшить следующие планы.")
    sid = st.session_state.student_id

    resp = api_request("GET", f"/plans/{sid}/history?limit=1")
    if resp.status_code != 200 or not resp.json().get("plans"):
        st.info("Нет планов для обратной связи"); return
    plan = resp.json()["plans"][0]
    ex_resp = api_request("GET", f"/plans/{plan['plan_id']}/exercises")
    if ex_resp.status_code != 200:
        return
    exercises = [e for e in ex_resp.json()["exercises"] if e["status"] == "SCHEDULED"]
    if not exercises:
        st.success("🎉 Все упражнения отмечены!")
        return

    st.markdown(f"**План от {plan['date']}** — осталось отметить: {len(exercises)}")
    for ex in exercises:
        with st.container(border=True):
            st.markdown(f"**{ex['exercise_name']}** ({ex['recommended_sets']}×{ex['recommended_reps']})")
            c1, c2, c3 = st.columns([1, 1, 2])
            completed = c1.checkbox("Выполнено", key=f"done_{ex['assigned_exercise_id']}")
            difficulty = c2.selectbox("Сложность", ["Very Easy", "Easy", "Normal", "Hard", "Very Hard"],
                                      index=2, key=f"diff_{ex['assigned_exercise_id']}")
            if st.button("💾 Сохранить", key=f"save_{ex['assigned_exercise_id']}"):
                payload = {
                    "assigned_exercise_id": ex["assigned_exercise_id"],
                    "completed": completed,
                    "actually_sets": ex["recommended_sets"] if completed else 0,
                    "actually_reps": ex["recommended_reps"] if completed else 0,
                    "perceived_difficulty": difficulty,
                    "exercise_status": "COMPLETED" if completed else "SKIPPED"
                }
                r = api_request("POST", "/interactions", json=payload)
                if r.status_code == 200:
                    st.success("✅ Сохранено!")
                    st.rerun()
                else:
                    st.error(f"❌ {r.json().get('detail')}")

# ── Teacher Pages ───────────────────────────────────────────────────────────
def teacher_students():
    st.title("👥 Управление студентами")
    
    # Поиск студента
    col1, col2 = st.columns([1, 3])
    with col1:
        search = st.text_input("🔍 ID студента", placeholder="1-500")
    with col2:
        st.info("Введите ID студента для просмотра детальной аналитики, планов и истории")
    
    if not search:
        st.markdown("### 📊 Быстрая статистика")
        st.info("Выберите студента для детального просмотра")
        return
    
    try:
        sid = int(search)
    except ValueError:
        st.warning("Введите число"); return
    
    # Загружаем данные студента
    resp = api_request("GET", f"/students/{sid}")
    if resp.status_code != 200:
        st.error("Студент не найден"); return
    p = resp.json()
    
    # Заголовки
    st.markdown("---")
    st.markdown(f"## 🎓 {p['name']} (ID: {sid})")
    
    # Основная информация
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Возраст", f"{p['age']}")
    c2.metric("Пол", p["gender"])
    c3.metric("Мед. группа", p["medical_group"])
    c4.metric("ИМТ", f"{p['biometrics']['bmi']:.1f}")
    c5.metric("Уровень", 
              f"{(p['assessment_scores']['strength']+p['assessment_scores']['endurance']+p['assessment_scores']['flexibility'])/3:.1f}/4")
    
    # Табы для разных разделов
    tab_profile, tab_plans, tab_interactions, tab_ai = st.tabs([
        "📋 Профиль", "📅 Планы", "💬 История", "🧠 ИИ-аналитика"
    ])
    
    with tab_profile:
        st.markdown("### 🏃 Кардио-выносливость")
        fig_cooper = go.Figure()
        fig_cooper.add_trace(go.Indicator(
            mode="gauge+number",
            value=p["fitness_metrics"]["cooper_meters"],
            title={"text": "Тест Купера (метры)"},
            gauge={
                "axis": {"range": [800, 3500]},
                "bar": {"color": "#4CAF50"},
                "steps": [
                    {"range": [800, 2000], "color": "#ffcdd2"},
                    {"range": [2000, 2400], "color": "#fff9c4"},
                    {"range": [2400, 2800], "color": "#c8e6c9"},
                    {"range": [2800, 3500], "color": "#a5d6a7"}
                ]
            }
        ))
        fig_cooper.update_layout(height=200)
        st.plotly_chart(fig_cooper, use_container_width=True)
        
        st.markdown("### 💪 Силовые показатели")
        metrics = p["fitness_metrics"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Отжимания", "Подтягивания", "Пресс", "Гибкость", "Прыжок"],
            y=[metrics["push_ups"], metrics["pull_ups"], metrics["sit_ups"],
               metrics["flexibility"], metrics["jump_forward"]],
            marker_color=["#2196F3", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"]
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        if p["active_injuries"]:
            st.markdown("### ⚠️ Активные травмы")
            for inj in p["active_injuries"]:
                st.warning(f"**{inj['type']}** ({inj['region']}) — до {inj['recovery_date']}")
        else:
            st.success("✅ Травм нет")
    
    with tab_plans:
        st.markdown("### 📅 История планов тренировок")
        
        if st.button("✨ Сгенерировать новый план", type="primary"):
            with st.spinner("ИИ генерирует план..."):
                gen_resp = api_request("POST", "/plans/generate", json={"student_id": sid, "save_to_db": True})
                if gen_resp.status_code == 200:
                    st.success("✅ План создан!")
                    st.rerun()
                else:
                    st.error(f"❌ {gen_resp.json().get('detail')}")
        
        plans_resp = api_request("GET", f"/plans/{sid}/history?limit=10")
        if plans_resp.status_code != 200:
            st.error("Ошибка загрузки планов"); return
        
        plans = plans_resp.json().get("plans", [])
        if not plans:
            st.info("📭 У студента пока нет планов")
            return
        
        for plan in plans:
            with st.expander(f"📋 План от {plan['date']} — {plan['status']}", expanded=(plan == plans[0])):
                ex_resp = api_request("GET", f"/plans/{plan['plan_id']}/exercises")
                if ex_resp.status_code != 200:
                    continue
                exercises = ex_resp.json()["exercises"]
                
                for day in ["MONDAY", "WEDNESDAY", "FRIDAY"]:
                    day_exs = [e for e in exercises if e["day_of_week"] == day]
                    if not day_exs:
                        continue
                    st.markdown(f"**🗓️ {day}**")
                    for ex in day_exs:
                        status_emoji = {"COMPLETED": "✅", "SKIPPED": "⏭️", "SCHEDULED": "⏰", "DISCARDED": "❌"}.get(ex["status"], "❔")
                        slot_emoji = {"warmup": "🔥", "main": "💪", "cooldown": "🧘"}.get(ex["slot_type"], "")
                        st.markdown(f"{status_emoji} {slot_emoji} **{ex['exercise_name']}** — {ex['recommended_sets']}×{ex['recommended_reps']} "
                                    f"*({ex['slot_type']}, score: {ex['predicted_score']:.2f})*")
    
    with tab_interactions:
        st.markdown("### 💬 История взаимодействий")
        
        int_resp = api_request("GET", f"/interactions/{sid}/summary")
        if int_resp.status_code != 200:
            st.error("Ошибка загрузки"); return
        
        stats = int_resp.json().get("exercise_stats", [])
        if not stats:
            st.info("Нет данных о взаимодействиях")
            return
        
        df = pd.DataFrame(stats)
        
        st.markdown("#### 📊 Общая статистика")
        c1, c2, c3 = st.columns(3)
        c1.metric("Упражнений выполнено", len(df))
        c2.metric("Средний % завершения", f"{df['completion_rate'].mean()*100:.0f}%")
        c3.metric("Средняя сложность", f"{df['avg_difficulty'].mean():.1f}/5")
        
        st.markdown("#### 📋 Детализация по упражнениям")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # График топ упражнений
        st.markdown("#### 🏆 Топ-5 упражнений по completion rate")
        top5 = df.nlargest(5, "completion_rate")
        fig = px.bar(top5, x="exercise", y="completion_rate",
                     color="avg_difficulty", color_continuous_scale="RdYlGn",
                     labels={"completion_rate": "Completion Rate", "exercise": "Упражнение", "avg_difficulty": "Сложность"})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab_ai:
        st.markdown("### 🧠 Объяснение ИИ")
        st.markdown("ИИ проанализирует профиль студента и объяснит логику построения плана")
        
        if st.button("🔍 Сгенерировать объяснение плана", type="primary"):
            with st.spinner("ИИ анализирует..."):
                exp_resp = api_request("GET", f"/explain/plan/{sid}/ru")
                if exp_resp.status_code == 200:
                    st.code(exp_resp.json()["explanation"], language=None)
                else:
                    st.error("Не удалось получить объяснение")
        
        st.markdown("---")
        st.markdown("### 📈 SHAP-анализ (для разработчиков)")
        st.info("SHAP-графики показывают, какие факторы влияют на рекомендации ИИ")
        
        if st.button("📊 Сгенерировать SHAP-график"):
            with st.spinner("Генерирую SHAP-анализ..."):
                shap_resp = api_request("GET", f"/explain/plan/{sid}/shap-plot")
                if shap_resp.status_code == 200:
                    st.image(shap_resp.content)
                else:
                    st.error("Ошибка генерации")
                    
def teacher_model():
    st.title("🤖 Управление моделью")
    resp = api_request("GET", "/model/status")
    if resp.status_code != 200:
        st.error("Ошибка"); return
    status = resp.json()

    c1, c2, c3 = st.columns(3)
    c1.metric("Модель загружена", "✅" if status["model_loaded"] else "❌")
    c2.metric("Готово к ретрейну", "✅" if status["retrain_ready"] else "❌")
    c3.metric("Новых взаимодействий", f"{status['new_interactions']} / {status['threshold']}")

    st.progress(min(status["new_interactions"] / status["threshold"], 1.0),
                text=f"Прогресс накопления данных: {status['new_interactions']}/{status['threshold']}")

    if st.button("🔄 Запустить ретрейнинг", type="primary"):
        force = st.checkbox("Принудительно (игнорировать порог)")
        if st.button("⚡ Подтвердить"):
            with st.spinner("Модель переобучается в фоне..."):
                r = api_request("POST", "/model/retrain", json={"force": force})
                if r.status_code == 200:
                    st.success(r.json().get("message", "Запущено"))
                else:
                    st.error(r.json().get("detail"))

    st.markdown("### 📜 История ретрейнов")
    hist_resp = api_request("GET", "/model/retrain/history")
    if hist_resp.status_code == 200:
        history = hist_resp.json()["history"]
        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("История пуста")

# ── Navigation ──────────────────────────────────────────────────────────────
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
        st.markdown(f"*API: {API_URL}*")

    # Pages
    if st.session_state.role == "student":
        pages = [
            st.Page(student_dashboard, title="🏠 Профиль", icon="🏠"),
            st.Page(student_fatigue, title="💪 Мышцы", icon="💪"),
            st.Page(student_plan, title="📅 Планы", icon="📅"),
            st.Page(student_feedback, title="💬 Обратная связь", icon="💬"),
        ]
    else:
        pages = [
            st.Page(teacher_students, title="👥 Студенты", icon="👥"),
            st.Page(teacher_model, title="🤖 Модель", icon="🤖"),
        ]

    pg = st.navigation(pages)
    pg.run()

if __name__ == "__main__":
    main()