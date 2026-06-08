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
    st.title(" Управление студентами")
    
    # Search bar
    col1, col2 = st.columns([1, 3])
    with col1:
        search = st.text_input("🔍 ID студента", placeholder="1-500")
    with col2:
        st.info("Введите ID для просмотра и редактирования данных")
    
    if not search:
        return
    
    try:
        sid = int(search)
    except ValueError:
        st.warning("Введите число"); return
    
    # Load student data
    resp = api_request("GET", f"/students/{sid}")
    if resp.status_code != 200:
        st.error("Студент не найден"); return
    p = resp.json()
    
    st.markdown("---")
    st.markdown(f"##  {p['name']} (ID: {sid})")
    
    # 4 Tabs as per your diagram
    tab_data, tab_generate, tab_scheduled, tab_history = st.tabs([
        "📋 Данные студента", 
        "✨ Генерация плана", 
        " Запланированные тренировки", 
        " История тренировок"
    ])
    
    with tab_data:
        _tab_student_data(sid, p)
    
    with tab_generate:
        _tab_generate_plan(sid)
    
    with tab_scheduled:
        _tab_scheduled_workouts(sid)
    
    with tab_history:
        _tab_workout_history(sid)


def _tab_student_data(sid, p):
    """Tab 1: View and edit student profile, injuries, muscle fatigue."""
    st.markdown("### 📊 Профиль и медицинские данные")
    
    # Edit Health Profile
    with st.expander("️ Редактировать мед. профиль", expanded=True):
        with st.form("edit_profile_form"):
            c1, c2, c3 = st.columns(3)
            height = c1.number_input("Рост (см)", value=p["biometrics"]["height_cm"])
            weight = c2.number_input("Вес (кг)", value=p["biometrics"]["weight_kg"])
            mg_id = c3.number_input("Мед. группа ID (1-3)", value=p["medical_group_id"], min_value=1, max_value=3)
            
            c4, c5, c6 = st.columns(3)
            cooper = c4.number_input("Тест Купера (м)", value=p["fitness_metrics"]["cooper_meters"])
            pushups = c5.number_input("Отжимания", value=p["fitness_metrics"]["push_ups"])
            pullups = c6.number_input("Подтягивания", value=p["fitness_metrics"]["pull_ups"])
            
            c7, c8, c9 = st.columns(3)
            flex = c7.number_input("Гибкость (см)", value=p["fitness_metrics"]["flexibility"])
            situps = c8.number_input("Пресс", value=p["fitness_metrics"]["sit_ups"])
            jump = c9.number_input("Прыжок (см)", value=p["fitness_metrics"]["jump_forward"])
            
            if st.form_submit_button("💾 Сохранить изменения"):
                payload = {
                    "height_cm": height, "weight_kg": weight, "medical_group_id": mg_id,
                    "cooper_meters": cooper, "push_ups": pushups, "pull_ups": pullups,
                    "flexibility_cm": flex, "sit_ups": situps, "jump_forward": jump
                }
                r = api_request("PUT", f"/students/{sid}/health-profile", json=payload)
                if r.status_code == 200:
                    st.success("✅ Профиль обновлен!")
                    st.rerun()
                else:
                    st.error(f"❌ {r.json().get('detail')}")
    
    # Injuries
    st.markdown("### ️ История травм")
    injuries = p.get("active_injuries", [])
    if injuries:
        for inj in injuries:
            with st.container(border=True):
                st.markdown(f"**{inj['type']}** ({inj['region']}) — до {inj['recovery_date']}")
                if st.button(f"✅ Отметить как восстановленную", key=f"heal_{inj['type']}"):
                    # In real app, you'd need the injury_record_id. For now, we'd need to fetch it.
                    st.info("Функция требует injury_record_id. Добавьте эндпоинт для получения ID.")
    else:
        st.success("Травм нет")
    
    with st.expander("➕ Добавить новую травму"):
        with st.form("add_injury_form"):
            inj_type = st.number_input("Injury Type ID (1-7)", min_value=1, max_value=7)
            diag_date = st.date_input("Дата диагностики")
            rec_date = st.date_input("Дата восстановления (опционально)")
            status = st.selectbox("Статус", ["active", "recovered"])
            if st.form_submit_button("Добавить травму"):
                payload = {
                    "injury_type_id": inj_type,
                    "diagnosis_date": str(diag_date),
                    "recovery_date": str(rec_date) if rec_date else None,
                    "recovery_status": status
                }
                r = api_request("POST", f"/students/{sid}/injuries", json=payload)
                if r.status_code == 200:
                    st.success("Травма добавлена!")
                    st.rerun()
                else:
                    st.error(f"❌ {r.json().get('detail')}")
    
    # Muscle Fatigue
    st.markdown("###  Состояние мышц (Muscle Fatigue)")
    fat_resp = api_request("GET", f"/students/{sid}/muscle-fatigue")
    if fat_resp.status_code == 200:
        fatigue_data = fat_resp.json().get("active_fatigue", [])
        if fatigue_data:
            for f in fatigue_data:
                st.markdown(f"**{f['muscle']}** — {f['recovery_pct']:.0f}% восстановлено")
                if st.button(f"Отметить как восстановленную", key=f"mf_{f['muscle']}"):
                    st.info("Требуется muscle_fatigue_id для обновления.")
        else:
            st.success("Все мышцы восстановлены!")
    else:
        st.error("Не удалось загрузить данные об усталости мышц")


def _tab_generate_plan(sid):
    """Tab 2: Generate and edit a new weekly plan."""
    st.markdown("### ✨ Генерация плана тренировок на неделю")
    
    if st.button("🤖 Сгенерировать новый план", type="primary"):
        with st.spinner("ИИ генерирует план..."):
            r = api_request("POST", "/plans/generate", json={"student_id": sid, "save_to_db": True})
            if r.status_code == 200:
                st.success("✅ План создан!")
                st.rerun()
            else:
                st.error(f"❌ {r.json().get('detail')}")
    
    st.markdown("---")
    plans_resp = api_request("GET", f"/plans/{sid}/history?limit=1")
    if plans_resp.status_code != 200 or not plans_resp.json().get("plans"):
        st.info("Нет планов. Сгенерируйте первый!"); return
    
    latest_plan = plans_resp.json()["plans"][0]
    st.markdown(f"**Последний план:** {latest_plan['date']} (ID: {latest_plan['plan_id']})")
    
    ex_resp = api_request("GET", f"/plans/{latest_plan['plan_id']}/exercises")
    if ex_resp.status_code != 200:
        return
    
    exercises = ex_resp.json()["exercises"]
    
    for day in ["MONDAY", "WEDNESDAY", "FRIDAY"]:
        day_exs = [e for e in exercises if e["day_of_week"] == day]
        if not day_exs:
            continue
        st.markdown(f"#### 🗓️ {day}")
        for ex in day_exs:
            with st.container(border=True):
                st.markdown(f"**{ex['exercise_name']}** ({ex['slot_type']}) — {ex['recommended_sets']}×{ex['recommended_reps']}")
                c1, c2, c3 = st.columns([1, 1, 2])
                new_sets = c1.number_input("Подходы", value=ex['recommended_sets'], key=f"sets_{ex['assigned_exercise_id']}")
                new_reps = c2.number_input("Повторения", value=ex['recommended_reps'], key=f"reps_{ex['assigned_exercise_id']}")
                if c3.button("💾 Сохранить", key=f"save_{ex['assigned_exercise_id']}"):
                    payload = {"recommended_sets": new_sets, "recommended_reps": new_reps}
                    r = api_request("PATCH", f"/plans/{latest_plan['plan_id']}/exercises/{ex['assigned_exercise_id']}", json=payload)
                    if r.status_code == 200:
                        st.success("Обновлено!")
                        st.rerun()
                if st.button("🗑️ Удалить упражнение", key=f"del_{ex['assigned_exercise_id']}"):
                    r = api_request("DELETE", f"/plans/{latest_plan['plan_id']}/exercises/{ex['assigned_exercise_id']}")
                    if r.status_code == 200:
                        st.success("Удалено!")
                        st.rerun()
    
    if st.button("🧠 Объяснить почему ИИ создала такой план"):
        with st.spinner("Генерирую объяснение..."):
            exp_resp = api_request("GET", f"/explain/plan/{sid}/ru")
            if exp_resp.status_code == 200:
                st.code(exp_resp.json()["explanation"], language=None)
            else:
                st.error("Ошибка получения объяснения")
def _tab_scheduled_workouts(sid):
    """Tab 3: View and edit upcoming scheduled workouts."""
    st.markdown("### 📅 Запланированные тренировки")
    
    plans_resp = api_request("GET", f"/plans/{sid}/history?limit=10")
    if plans_resp.status_code != 200:
        return
    
    plans = [p for p in plans_resp.json().get("plans", []) if p["status"] == "SCHEDULED"]
    if not plans:
        st.info("Нет запланированных тренировок")
        return
    
    # Load all exercises for replacement option
    all_exercises_resp = api_request("GET", "/exercises")
    all_exercises = []
    if all_exercises_resp.status_code == 200:
        all_exercises = all_exercises_resp.json().get("exercises", [])
    
    exercise_options = {e['exercise_id']: e['exercise_name'] for e in all_exercises}
    
    for plan in plans:
        with st.expander(f"📋 План на {plan['date']} (ID: {plan['plan_id']})", expanded=True):
            ex_resp = api_request("GET", f"/plans/{plan['plan_id']}/exercises")
            if ex_resp.status_code != 200:
                continue
            exercises = ex_resp.json()["exercises"]
            
            for day in ["MONDAY", "WEDNESDAY", "FRIDAY"]:
                day_exs = [e for e in exercises if e["day_of_week"] == day]
                if not day_exs:
                    continue
                
                st.markdown(f"#### 🗓️ {day}")
                
                for ex in day_exs:
                    editing_key = f"editing_{ex['assigned_exercise_id']}"
                    is_editing = st.session_state.get(editing_key, False)
                    
                    with st.container(border=True):
                        if not is_editing:
                            # Display mode
                            st.markdown(f"**{ex['exercise_name']}** ({ex['slot_type']}) — {ex['recommended_sets']}×{ex['recommended_reps']}")
                            
                            c1, c2 = st.columns(2)
                            if c1.button("✏️ Редактировать", key=f"edit_btn_{ex['assigned_exercise_id']}"):
                                st.session_state[editing_key] = True
                                st.rerun()
                            if c2.button("🗑️ Удалить", key=f"del_btn_{ex['assigned_exercise_id']}"):
                                r = api_request("DELETE", f"/plans/{plan['plan_id']}/exercises/{ex['assigned_exercise_id']}")
                                if r.status_code == 200:
                                    st.success("Упражнение удалено!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {r.json().get('detail')}")
                        else:
                            # Edit mode — FIXED FORM
                            st.markdown(f"### Редактирование: **{ex['exercise_name']}**")
                            
                            with st.form(f"edit_form_{ex['assigned_exercise_id']}"):
                                c1, c2 = st.columns(2)
                                new_sets = c1.number_input(
                                    "Подходы", 
                                    value=ex['recommended_sets'], 
                                    min_value=1, 
                                    max_value=10,
                                    key=f"new_sets_{ex['assigned_exercise_id']}"
                                )
                                new_reps = c2.number_input(
                                    "Повторения", 
                                    value=ex['recommended_reps'], 
                                    min_value=1, 
                                    max_value=100,
                                    key=f"new_reps_{ex['assigned_exercise_id']}"
                                )
                                
                                # Option to replace exercise
                                st.markdown("---")
                                st.markdown("**Заменить упражнение:**")
                                
                                # Get current exercise_id safely
                                current_ex_id = ex.get('exercise_id')
                                if current_ex_id is None:
                                    st.error("Не удалось получить exercise_id. Обновите backend.")
                                    st.stop()
                                
                                selected_ex_id = st.selectbox(
                                    "Выберите новое упражнение",
                                    options=list(exercise_options.keys()),
                                    format_func=lambda x: exercise_options[x],
                                    index=list(exercise_options.keys()).index(current_ex_id) if current_ex_id in exercise_options else 0,
                                    key=f"sel_ex_{ex['assigned_exercise_id']}"
                                )
                                
                                # ✅ FIXED: Add proper submit buttons
                                c1, c2 = st.columns(2)
                                submitted = c1.form_submit_button(" Сохранить изменения", use_container_width=True)
                                cancelled = c2.form_submit_button(" Отмена", use_container_width=True)
                                
                                if submitted:
                                    payload = {
                                        "recommended_sets": new_sets,
                                        "recommended_reps": new_reps
                                    }
                                    if selected_ex_id != current_ex_id:
                                        payload["exercise_id"] = selected_ex_id
                                    
                                    r = api_request(
                                        "PATCH", 
                                        f"/plans/{plan['plan_id']}/exercises/{ex['assigned_exercise_id']}", 
                                        json=payload
                                    )
                                    if r.status_code == 200:
                                        st.success("✅ Изменения сохранены!")
                                        del st.session_state[editing_key]
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {r.json().get('detail')}")
                                
                                if cancelled:
                                    del st.session_state[editing_key]
                                    st.rerun()

def _tab_workout_history(sid):
    """Tab 4: View and edit past workout interactions."""
    st.markdown("### 📜 История тренировок")
    
    plans_resp = api_request("GET", f"/plans/{sid}/history?limit=10")
    if plans_resp.status_code != 200:
        return
    
    plans = [p for p in plans_resp.json().get("plans", []) if p["status"] in ["COMPLETED", "DISCARDED", "SKIPPED"]]
    if not plans:
        st.info("Нет завершенных тренировок")
        return
    
    for plan in plans:
        with st.expander(f"📋 Тренировка от {plan['date']} — {plan['status']}"):
            ex_resp = api_request("GET", f"/plans/{plan['plan_id']}/exercises")
            if ex_resp.status_code != 200:
                continue
            exercises = ex_resp.json()["exercises"]
            
            st.markdown("**Взаимодействия с упражнениями:**")
            for ex in exercises:
                if ex.get("completed") is not None:  # Has interaction data
                    with st.container(border=True):
                        st.markdown(f"**{ex['exercise_name']}**")
                        c1, c2, c3, c4 = st.columns(4)
                        completed = c1.checkbox("Выполнено", value=ex["completed"], key=f"hist_done_{ex['assigned_exercise_id']}")
                        sets = c2.number_input("Факт. подходы", value=ex.get("actually_sets") or 0, key=f"hist_sets_{ex['assigned_exercise_id']}")
                        reps = c3.number_input("Факт. повторы", value=ex.get("actually_reps") or 0, key=f"hist_reps_{ex['assigned_exercise_id']}")
                        diff = c4.selectbox("Сложность", ["Very Easy", "Easy", "Normal", "Hard", "Very Hard"], 
                                          index=["Very Easy", "Easy", "Normal", "Hard", "Very Hard"].index(ex.get("perceived_difficulty") or "Normal"),
                                          key=f"hist_diff_{ex['assigned_exercise_id']}")
                        
                        if st.button("💾 Сохранить изменения", key=f"hist_save_{ex['assigned_exercise_id']}"):
                            # Note: You'd need the interaction_id here. For now, this is a placeholder.
                            st.info("Для редактирования истории требуется interaction_id. Добавьте его в ответ API.")
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