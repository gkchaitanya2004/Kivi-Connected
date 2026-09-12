import streamlit as st
from src.auth import get_sarvam_key, update_sarvam_key
from src.pages_.dictation import dictation_page
from src.pages_.conversations import conversations_page

def home_page(cookies):
    with st.sidebar:
        st.write(f"### 👤 {st.session_state['user']}")
        st.divider()
        st.write("#### Sarvam API Key")

        current_key = get_sarvam_key(st.session_state["user"]) or ""
        new_key = st.text_input("API Key", value=current_key, type="password", label_visibility="collapsed")
        st.caption("Get your key from [indus.sarvam.ai](https://indus.sarvam.ai) → sign up → API Keys → generate key.")

        if st.button("Save Key", use_container_width=True):
            if not new_key.strip():
                st.error("API key cannot be empty.")
            else:
                update_sarvam_key(st.session_state["user"], new_key)
                st.success("Saved.")

        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.pop("logged_in", None)
            st.session_state.pop("user", None)
            cookies["user"] = ""
            cookies.save()
            st.session_state["just_logged_out"] = True
            st.rerun()

    st.title(f"Welcome, {st.session_state['user']}")
    tab1, tab2 = st.tabs(["Dictations", "Conversations"])
    with tab1:
        dictation_page()
    with tab2:
        conversations_page()