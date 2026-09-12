import streamlit as st
from src.auth import add_user, is_valid_email, is_valid_password

def signup_page():
    with st.form("signup_form"):
        new_email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
        new_password = st.text_input("Password", type="password", placeholder="••••••••", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

        if submitted:
            if not is_valid_email(new_email):
                st.error("Please enter a valid email address.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                pw_error = is_valid_password(new_password)
                if pw_error:
                    st.error(pw_error)
                else:
                    if add_user(new_email, new_password):
                        st.success("Account created. Please log in.")
                    else:
                        st.error("An account with this email already exists.")