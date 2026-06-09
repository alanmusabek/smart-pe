import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.api import api_request

def render_dashboard():
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
    c4.metric("🎯 Уровень", f"{(p['assessment_scores']['strength']+p['assessment_scores']['endurance']+p['assessment_scores']['flexibility'])/3:.1f}/4")

    st.markdown("### 🏃 Кардио-выносливость")
    fig_cooper = go.Figure()
    fig_cooper.add_trace(go.Indicator(
        mode="gauge+number", value=p["fitness_metrics"]["cooper_meters"],
        title={"text": "Тест Купера (метры)"},
        gauge={
            "axis": {"range": [800, 3500]}, "bar": {"color": "#4CAF50"},
            "steps": [
                {"range": [800, 2000], "color": "#ffcdd2"},
                {"range": [2000, 2400], "color": "#fff9c4"},
                {"range": [2400, 2800], "color": "#c8e6c9"},
                {"range": [2800, 3500], "color": "#a5d6a7"}
            ],
            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 2800}
        }
    ))
    fig_cooper.update_layout(height=250)
    st.plotly_chart(fig_cooper, use_container_width=True)

    st.markdown("### 💪 Силовые показатели и гибкость")
    metrics = p["fitness_metrics"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Отжимания", "Подтягивания", "Пресс", "Гибкость (см)", "Прыжок (см)"],
        y=[metrics["push_ups"], metrics["pull_ups"], metrics["sit_ups"], metrics["flexibility"], metrics["jump_forward"]],
        marker_color=["#2196F3", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"],
        text=[metrics["push_ups"], metrics["pull_ups"], metrics["sit_ups"], f"{metrics['flexibility']:.1f}", metrics["jump_forward"]],
        textposition="auto"
    ))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    if p["active_injuries"]:
        st.markdown("### ⚠️ Активные травмы")
        for inj in p["active_injuries"]:
            st.warning(f"**{inj['type']}** ({inj['region']}) — до {inj['recovery_date']}")

def render_fatigue():
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

def render_plan():
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
                    slot_emoji = {"warmup": "🔥", "main": "💪", "cooldown": "🧘"}.get(ex["slot_type"], " ")
                    st.markdown(f"{status_emoji} {slot_emoji} **{ex['exercise_name']}** — {ex['recommended_sets']}×{ex['recommended_reps']}  "
                                f"*({ex['slot_type']}, score: {ex['predicted_score']:.2f})*")

            if st.button(f"🧠 Почему ИИ выбрал этот план?", key=f"explain_{plan['plan_id']}"):
                with st.spinner("Генерирую объяснение..."):
                    exp_resp = api_request("GET", f"/explain/plan/{sid}/ru")
                    if exp_resp.status_code == 200:
                        st.markdown("### 🧠 Объяснение ИИ")
                        st.code(exp_resp.json()["explanation"], language=None)
                    else:
                        st.error("Не удалось получить объяснение")

def render_feedback():
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
            difficulty = c2.selectbox("Сложность", ["Very Easy", "Easy", "Normal", "Hard", "Very Hard"], index=2, key=f"diff_{ex['assigned_exercise_id']}")
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