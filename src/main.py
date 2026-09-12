import streamlit as st
from PIL import Image
import sys
from pathlib import Path
from streamlit_cookies_manager import EncryptedCookieManager

sys.path.append(str(Path(__file__).parent.parent))

from src.auth import init_db,create_history_table
from src.pages_.login import login_page
from src.pages_.signup import signup_page
from src.pages_.home import home_page

app_icon = Image.open("src/assets/logo.png")
st.set_page_config(
    page_title="Kivi Threadline",
    page_icon=app_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

create_history_table()

cookies = EncryptedCookieManager(prefix="kivi_", password="some-long-random-secret-string")
if not cookies.ready():
    st.stop()

if (
    not st.session_state.get("logged_in")
    and not st.session_state.get("just_logged_out")
    and cookies.get("user")
):
    st.session_state["logged_in"] = True
    st.session_state["user"] = cookies["user"]

st.session_state.pop("just_logged_out", None)

if st.session_state.get("logged_in"):
    home_page(cookies)
else:
    left, center, right = st.columns([1, 1.5, 1])
    with center:
        st.markdown(
            """
            <h1 style="text-align: center;">Kivi Threadline</h1>
            <p style="text-align: center; color: gray;">Your notes and conversations, one memory.</p>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            login_page(cookies)
        with tab2:
            signup_page()