import streamlit as st
from src.auth import verify_user

def login_page(cookies):

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            if verify_user(email, password):
                st.session_state["logged_in"] = True
                st.session_state["user"] = email
                cookies["user"] = email
                cookies.save()
                st.rerun()
            else:
                st.error("Invalid email or password.")