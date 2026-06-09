import streamlit as st
import requests

API_URL = "http://localhost:8000"

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