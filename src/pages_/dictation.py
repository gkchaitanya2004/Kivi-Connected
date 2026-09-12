import streamlit as st
import tempfile
import os
from sarvamai import SarvamAI
from src.auth import add_history, get_history, get_sarvam_key,create_memory_table, add_memory_entry
from src.pages_.memory_store import add_memory_embedding, create_memory_collection

def dictation_page():
    email = st.session_state["user"]

    st.title("Dictation")
    tab1, tab2 = st.tabs(["Paste Text", "Upload Audio"])

    with tab1:
        with st.form("paste_text_form"):
            pasted_text = st.text_area("Paste your text", height=150)
            submitted = st.form_submit_button("Save", type="primary", use_container_width=True)

            if submitted:
                if not pasted_text.strip():
                    st.error("Text cannot be empty.")
                else:
                    add_history(email, pasted_text.strip())
                    st.success("Saved to history.")
                    st.rerun()

    with tab2:
        audio_file = st.audio_input("Record high quality audio", sample_rate=48000)

        if st.button("Transcribe & Save", type="primary", use_container_width=True):
            if audio_file:
                api_key = get_sarvam_key(email)
                if not api_key:
                    st.error("Add your Sarvam API key in the sidebar first.")
                else:
                    with st.spinner("Transcribing..."):
                        tmp_path = None
                        try:
                            # Sarvam's SDK expects a file path, so write the upload to a temp file
                            suffix = os.path.splitext(audio_file.name or "audio.wav")[1] or ".wav"
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(audio_file.getvalue())
                                tmp_path = tmp.name

                            client = SarvamAI(api_subscription_key=api_key)
                            with open(tmp_path, "rb") as audio:
                                response = client.speech_to_text.transcribe(
                                    file=audio,
                                    model="saaras:v3",
                                )
                            transcript = response.transcript

                            if transcript.strip():
                                add_history(email, transcript.strip())
                                st.success("Transcribed and saved to history.")
                                st.rerun()
                            else:
                                st.warning("Transcription came back empty.")
                        except Exception as e:
                            st.error(f"Transcription failed: {e}")
                        finally:
                            if tmp_path:
                                try:
                                    os.remove(tmp_path)
                                except OSError:
                                    pass

        # =========================
    # HISTORY
    # =========================
    st.write("### History")

    history_rows = get_history(email)
    history = [row[1] for row in history_rows]  # Extract only the

    if not history:
        st.caption("No entries yet.")

    else:

        # ---------------------------------
        # Helper: update Select All
        # ---------------------------------
        def update_select_all():
            all_selected = all(
                st.session_state.get(f"select_history_{i}", False)
                for i in range(len(history))
            )

            st.session_state["select_all_history"] = all_selected

        # ---------------------------------
        # Select All callback
        # ---------------------------------
        def toggle_select_all():
            select_all = st.session_state["select_all_history"]

            for i in range(len(history)):
                st.session_state[f"select_history_{i}"] = select_all

        # Count selected items
        selected_count = sum(
            st.session_state.get(f"select_history_{i}", False)
            for i in range(len(history))
        )

        # ---------------------------------
        # Header
        # ---------------------------------
        header_col1, header_col2 = st.columns([0.75, 0.25])

        with header_col1:
            st.checkbox(
                "Select all",
                key="select_all_history",
                on_change=toggle_select_all,
            )

        with header_col2:
            st.markdown(
                f"""
                <div style="
                    text-align:right;
                    padding-top:8px;
                    color:#9ca3af;
                    font-size:14px;
                ">
                    {selected_count} selected
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---------------------------------
        # Scrollable History Container
        # ---------------------------------
        with st.container(height=400, border=True):

            for index, entry in enumerate(history):

                # Make sure checkbox exists in session state
                checkbox_key = f"select_history_{index}"

                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False

                is_selected = st.session_state[checkbox_key]

                left_col, right_col = st.columns(
                    [0.025, 0.975],
                    gap="small"
                )

                with left_col:
                    st.checkbox(
                        "select",
                        key=checkbox_key,
                        label_visibility="collapsed",
                        on_change=update_select_all,
                    )

                with right_col:

                    # History card
                    if is_selected:
                        border = "#4f46e5"
                        background = "rgba(79, 70, 229, 0.10)"
                    else:
                        border = "#30343b"
                        background = "rgba(255, 255, 255, 0.02)"

                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid {border};
                            background: {background};
                            border-radius: 10px;
                            padding: 12px 15px;
                            margin-bottom: 10px;
                            min-height: 45px;
                            line-height: 1.5;
                        ">
                            <div style="
                                color: #e5e7eb;
                                font-size: 15px;
                            ">
                                {entry}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # ---------------------------------
        # Get selected texts
        # ---------------------------------
        selected_entries = [
            entry
            for idxs, entry in enumerate(history_rows)
            if st.session_state.get(f"select_history_{idxs}", False)
        ]

        # ---------------------------------
        # Add to Kivi Memory Button
        # ---------------------------------
        st.write("")

        if st.button(
            f"Add to Kivi Memory ({len(selected_entries)} selected)",
            type="primary",
            use_container_width=True,
            disabled=len(selected_entries) == 0,
        ):

            # Create memory table if it doesn't exist
            create_memory_table()
            

            for history_id, entry in selected_entries:
                memory_id = add_memory_entry(
                    entry_type="dictation",
                    email=email,
                    entry=entry,
                    history_id=history_id
                )


                add_memory_embedding(
                    email=email,
                    ids=memory_id,
                    docs=entry,
                    metadatas={"type": "dictation", "history_id": history_id}
                )


            st.success(f"Added {len(selected_entries)} entries to Kivi Memory.")