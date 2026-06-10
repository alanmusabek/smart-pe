import streamlit as st
import pandas as pd
from utils.api import api_request

def render_students():
    st.title("👥 Управление студентами")
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

    resp = api_request("GET", f"/students/{sid}")
    if resp.status_code != 200:
        st.error("Студент не найден"); return
    p = resp.json()

    st.markdown("---")
    st.markdown(f"## {p['name']} (ID: {sid})")

    tab_data, tab_generate, tab_scheduled, tab_history = st.tabs([
        "📋 Данные студента", "✨ Генерация плана", "📅 Запланированные тренировки", "📜 История тренировок"
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
    st.markdown("### 📊 Профиль и медицинские данные")
    with st.expander("✏️ Редактировать мед. профиль", expanded=True):
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

    st.markdown("### 🩹 История травм")
    injuries = p.get("active_injuries", [])
    if injuries:
        for inj in injuries:
            with st.container(border=True):
                st.markdown(f"**{inj['type']}** ({inj['region']}) — до {inj['recovery_date']}")
                if st.button(f"✅ Отметить как восстановленную", key=f"heal_{inj['type']}"):
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
                    "injury_type_id": inj_type, "diagnosis_date": str(diag_date),
                    "recovery_date": str(rec_date) if rec_date else None, "recovery_status": status
                }
                r = api_request("POST", f"/students/{sid}/injuries", json=payload)
                if r.status_code == 200:
                    st.success("Травма добавлена!")
                    st.rerun()
                else:
                    st.error(f"❌ {r.json().get('detail')}")

    st.markdown("### 🦵 Состояние мышц (Muscle Fatigue)")
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
    
    # Show the latest plan with all three days
    st.markdown(f"## 📋 План от {latest_plan['date']} (ID: {latest_plan['plan_id']}) - {latest_plan['status']}")
    
    ex_resp = api_request("GET", f"/plans/{latest_plan['plan_id']}/exercises")
    if ex_resp.status_code != 200:
        st.error("Не удалось загрузить упражнения"); return

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
    st.markdown("### 📅 Запланированные тренировки")
    plans_resp = api_request("GET", f"/plans/{sid}/history?limit=10")
    if plans_resp.status_code != 200:
        return

    plans = [p for p in plans_resp.json().get("plans", []) if p["status"] == "SCHEDULED"]
    if not plans:
        st.info("Нет запланированных тренировок")
        return

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
                            st.markdown(f"### Редактирование: **{ex['exercise_name']}**")
                            with st.form(f"edit_form_{ex['assigned_exercise_id']}"):
                                c1, c2 = st.columns(2)
                                new_sets = c1.number_input("Подходы", value=ex['recommended_sets'], min_value=1, max_value=10, key=f"new_sets_{ex['assigned_exercise_id']}")
                                new_reps = c2.number_input("Повторения", value=ex['recommended_reps'], min_value=1, max_value=100, key=f"new_reps_{ex['assigned_exercise_id']}")
                                
                                st.markdown("---")
                                st.markdown("**Заменить упражнение:**")
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
                                
                                c1, c2 = st.columns(2)
                                submitted = c1.form_submit_button("💾 Сохранить изменения", use_container_width=True)
                                cancelled = c2.form_submit_button("❌ Отмена", use_container_width=True)
                                
                                if submitted:
                                    payload = {"recommended_sets": new_sets, "recommended_reps": new_reps}
                                    if selected_ex_id != current_ex_id:
                                        payload["exercise_id"] = selected_ex_id
                                    
                                    r = api_request("PATCH", f"/plans/{plan['plan_id']}/exercises/{ex['assigned_exercise_id']}", json=payload)
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
                if ex.get("completed") is not None:
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
                            st.info("Для редактирования истории требуется interaction_id. Добавьте его в ответ API.")

def render_model():
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