import streamlit as st
import time
from utils.api import api_request

def render_chatbot():
    """Render the AI Coach chatbot interface."""
    st.title("🤖 AI Coach")
    st.markdown("### Ваш персональный ИИ-тренер")
    st.markdown("Задавайте вопросы о тренировках, планах, восстановлении мышц и многом другом!")
    
    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Sidebar settings
    with st.sidebar:
        st.markdown("### ⚙️ Настройки")
        
        # Check API status
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            if st.button("🔄 Обновить", use_container_width=True):
                st.rerun()
        
        # Show debug info
        show_debug = st.checkbox("🐛 Debug режим", value=False)
        
        if st.button("🗑️ Очистить чат", use_container_width=True, type="secondary"):
            st.session_state.chat_messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("**Поддерживаемые запросы:**")
        st.markdown("- 💪 'Сгенерируй план тренировок'")
        st.markdown("- 🔍 'Проверить усталость мышц'")
        st.markdown("- ❓ 'Почему выбрано это упражнение?'")
        st.markdown("- 📊 'Мой прогресс'")
        st.markdown("- 🏋️ 'Рекомендуй упражнения'")
        st.markdown("- 👋 'Привет', 'Помощь'")
    
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])
            
            # Show metadata if available and debug mode is on
            if show_debug and message.get("metadata"):
                with st.expander("📊 Метаданные ответа"):
                    st.json(message["metadata"])
    
    # Chat input
    if prompt := st.chat_input("Спросите ИИ-тренера о чём угодно..."):
        # Add user message to chat history
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt,
            "avatar": "👤"
        })
        
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            
            # Show thinking indicator
            with st.spinner("🤔 ИИ анализирует ваш запрос..."):
                try:
                    # Call the chatbot API
                    response = api_request(
                        "POST",
                        "/chat/",
                        json={"text": prompt}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract response content
                        ai_message = data.get("message", "Извините, я не понял ваш вопрос.")
                        intent = data.get("intent", "unknown")
                        confidence = data.get("confidence", 0.0)
                        action = data.get("action", "chat")
                        llm_used = data.get("llm_used", False)
                        response_data = data.get("data", {})
                        
                        # Build response display
                        full_response = ai_message
                        
                        # Add action-specific visualizations
                        if action == "plan_generated" and response_data:
                            st.success("✅ План сгенерирован!")
                            
                            # Display exercises in a nice format
                            if "exercises" in response_data:
                                st.markdown("#### 📋 Ваши упражнения:")
                                for idx, exercise in enumerate(response_data["exercises"], 1):
                                    with st.container(border=True):
                                        col1, col2 = st.columns([3, 1])
                                        with col1:
                                            st.markdown(f"**{idx}. {exercise.get('name', 'Unknown')}**")
                                            st.markdown(f"Фокус: {exercise.get('focus', 'N/A')}")
                                        with col2:
                                            st.metric("Подходы", exercise.get('sets', 'N/A'))
                                            st.metric("Повторы", exercise.get('reps', 'N/A'))
                        
                        elif action == "show_fatigue" and response_data:
                            st.info("📊 Состояние мышц")
                            
                            # Display muscle recovery as progress bars
                            if isinstance(response_data, dict):
                                for muscle, recovery_pct in response_data.items():
                                    emoji = "🟢" if recovery_pct > 70 else "🟡" if recovery_pct > 40 else "🔴"
                                    st.progress(recovery_pct / 100, text=f"{emoji} **{muscle}**: {recovery_pct:.0f}% восстановлено")
                        
                        elif action == "show_progress" and response_data:
                            st.info("📈 Ваш прогресс")
                            if isinstance(response_data, dict):
                                cols = st.columns(len(response_data))
                                for idx, (metric, value) in enumerate(response_data.items()):
                                    cols[idx].metric(metric.replace("_", " ").title(), f"{value:.1f}" if isinstance(value, float) else value)
                        
                        # Display the main message
                        message_placeholder.markdown(full_response)
                        
                        # Add LLM indicator if used
                        if llm_used and show_debug:
                            st.caption("✨ Ответ сгенерирован с помощью ИИ")
                        
                        # Store assistant response
                        metadata = {
                            "intent": intent,
                            "confidence": round(confidence, 3),
                            "action": action,
                            "llm_used": llm_used,
                            "timestamp": time.time()
                        }
                        
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": full_response,
                            "avatar": "🤖",
                            "metadata": metadata
                        })
                        
                    else:
                        error_msg = response.json().get("detail", "Произошла ошибка при обработке запроса")
                        message_placeholder.error(f"❌ {error_msg}")
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": f"❌ Ошибка: {error_msg}",
                            "avatar": "🤖"
                        })
                        
                except Exception as e:
                    error_message = f"⚠️ Не удалось получить ответ: {str(e)}"
                    message_placeholder.error(error_message)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "avatar": "🤖"
                    })
            
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.caption(
        "💡 **Совет:** Используйте естественный язык. Например: "
        "'Создай план на неделю', 'Как мои мышцы?', 'Почему именно приседания?'"
    )
