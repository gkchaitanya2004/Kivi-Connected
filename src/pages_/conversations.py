import streamlit as st
import base64
import json
import tempfile
import os
from pathlib import Path
from sarvamai import SarvamAI

from src.auth import get_sarvam_key
from src.pages_.memory_store import retrive_memory_embeddings, add_memory_embedding
from src.auth import voice_history_table, get_voice_history, add_voice_history
from src.auth import create_memory_table, add_memory_entry

PROCESSING_GIF_PATH = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "voice_processing.png"
)

voice_history_table()  # Ensure the voice_history table exists
create_memory_table()  # Ensure the memory table exists

@st.cache_data
def _load_gif_base64(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def build_system_prompt(memories):
    base = (
        "You are Hey Kivi, a helpful voice assistant. Answer general questions "
        "normally using your own knowledge. However, for anything about the "
        "user specifically — their facts, preferences, plans, or past "
        "conversations — you must rely ONLY on the memories listed below. "
        "If a personal question isn't answered by these memories, say you "
        "don't know that yet, rather than guessing. Keep answers short and "
        "conversational, since this will be spoken aloud.\n\n"
        "You must respond with ONLY a raw JSON object — no markdown fences, "
        "no preamble, nothing before or after it. The JSON object must have "
        "exactly these two keys:\n"
        '  "answer": the spoken reply to the user, as a plain string.\n'
        '  "memory_to_save": if, and only if, the user explicitly asked you to '
        "remember/save/note something about themselves, put that fact here as "
        "a short plain-text sentence (e.g. \"Favorite color is blue\"). If the "
        "user did not ask you to remember anything in this message, this key "
        "must be the JSON value null (not the string \"null\", not an empty "
        "string).\n\n"
        'Example: {"answer": "Got it, I will remember that.", '
        '"memory_to_save": "Favorite color is blue"}\n'
        'Example: {"answer": "It is sunny today.", "memory_to_save": null}'
    )
    if not memories:
        return base + "\n\nYou currently have no stored memories about this user."
    memory_lines = "\n".join(f"- {m}" for m in memories)
    return base + f"\n\nMemories about this user:\n{memory_lines}"


def get_chat_answer(api_key, question, memories):
    """Returns a dict: {"answer": str, "memory_to_save": str | None}."""
    client = SarvamAI(api_subscription_key=api_key)
    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[
            {"role": "system", "content": build_system_prompt(memories)},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        top_p=1,
        max_tokens=2000,
    )
    raw = response.choices[0].message.content

    # Strip accidental markdown fences before parsing.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    # The model sometimes prepends/appends plain text around the JSON
    # object despite instructions. Pull out just the {...} block so a
    # stray sentence before/after it doesn't break parsing.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    try:
        parsed = json.loads(cleaned)
        answer = parsed.get("answer", raw)
        memory_to_save = parsed.get("memory_to_save") or None
    except (json.JSONDecodeError, AttributeError):
        # Still not parseable — fall back to the plain text before the
        # JSON blob (if any), rather than dumping the raw JSON as speech.
        answer = raw[:start].strip() if start != -1 else raw
        memory_to_save = None

    return {"answer": answer, "memory_to_save": memory_to_save}


def synthesize_speech(api_key, text, language_code="en-IN"):
    client = SarvamAI(api_subscription_key=api_key)
    audio = client.text_to_speech.convert(
        text=text,
        language_code=language_code,
        model="bulbul:v3",
        speaker="pooja",
    )
    return base64.b64decode(audio.audios[0])


KIVI_CSS = """
<style>
.kivi-header { width: 100%; text-align: center; margin-bottom: 6px; }
.kivi-title { font-size: 30px; font-weight: 600; margin-top: 4px; margin-bottom: 2px; }
.kivi-subtitle { font-size: 14px; color: #9ca3af; margin-bottom: 14px; }

.kivi-chat-container {
    max-height: 60vh;
    overflow-y: auto;
    padding-right: 4px;
}

.st-key-reset_voice button {
    width: 220px !important;
    border-radius: 999px !important;
    font-size: 14px !important;
    margin: 15px auto 0 auto !important;
    display: block !important;
}
</style>
"""


def _reset_session():
    st.session_state.voice_turns = []
    st.session_state.voice_last_audio_hash = None
    st.session_state.voice_pending = False
    st.session_state.voice_autoplay_latest = False
    st.session_state.voice_audio_bytes = None


def conversations_page():
    if "voice_turns" not in st.session_state:
        st.session_state.voice_turns = []  # list of {question, answer, audio}
    if "voice_last_audio_hash" not in st.session_state:
        st.session_state.voice_last_audio_hash = None
    if "voice_pending" not in st.session_state:
        st.session_state.voice_pending = False

    st.markdown(KIVI_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="kivi-header">
            <div class="kivi-title">Kivi Voice</div>
            <div class="kivi-subtitle">Talk naturally with Kivi</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------- render conversation history as a chat thread ----------------
    chat_area = st.container()
    with chat_area:
        for i, turn in enumerate(st.session_state.voice_turns):
            with st.chat_message("user"):
                st.write(turn["question"])

            with st.chat_message("assistant"):
                st.write(turn["answer"])
                is_latest = i == len(st.session_state.voice_turns) - 1
                if turn.get("audio"):
                    st.audio(
                        turn["audio"],
                        format="audio/wav",
                        autoplay=is_latest and st.session_state.get("voice_autoplay_latest", False),
                    )

    # ---------------- processing indicator (shown as a pending assistant bubble) ----------------
    if st.session_state.voice_pending:
        with st.chat_message("assistant"):
            with st.spinner("Kivi is thinking..."):
                email = st.session_state["user"]
                api_key = get_sarvam_key(email)

                if not api_key:
                    st.error("Add your Sarvam API key in the sidebar first.")
                    st.session_state.voice_pending = False
                else:
                    try:
                        tmp_path = tempfile.mktemp(suffix=".wav")
                        with open(tmp_path, "wb") as f:
                            f.write(st.session_state.voice_audio_bytes)

                        client = SarvamAI(api_subscription_key=api_key)
                        with open(tmp_path, "rb") as f:
                            response = client.speech_to_text.transcribe(
                                file=f, model="saaras:v3", mode="transcribe",
                            )
                        transcript = response.transcript
                        os.remove(tmp_path)

                        if not transcript.strip():
                            raise ValueError("Transcription came back empty. Try speaking closer to the mic.")

                        results = retrive_memory_embeddings(email, transcript, n_results=5)
                        memories = results["documents"][0] if results and results.get("documents") else []

                        result = get_chat_answer(api_key, transcript, memories)
                        answer = result["answer"]
                        memory_to_save = result["memory_to_save"]

                        if memory_to_save:
                            memory_id = add_memory_entry(
                                entry_type="voice_chat",
                                email=email,
                                entry=memory_to_save,
                            )
                            add_memory_embedding(
                                email=email,
                                ids=memory_id,
                                docs=memory_to_save,
                                metadatas={"type": "voice_chat"},
                            )

                        audio_bytes = synthesize_speech(api_key, answer)

                        st.session_state.voice_turns.append({
                            "question": transcript,
                            "answer": answer,
                            "audio": audio_bytes,
                        })
                        st.session_state.voice_autoplay_latest = True

                    except Exception as e:
                        st.error(f"Something went wrong: {e}")

                    st.session_state.voice_pending = False
                    st.rerun()

    # ---------------- mic input, styled like a chat composer ----------------
    else:
        audio_value = st.audio_input(
            "Ask Kivi something", sample_rate=48000, label_visibility="collapsed"
        )

        if audio_value:
            audio_hash = hash(audio_value.getvalue())
            if audio_hash != st.session_state.voice_last_audio_hash:
                st.session_state.voice_last_audio_hash = audio_hash
                st.session_state.voice_audio_bytes = audio_value.getvalue()
                st.session_state.voice_pending = True
                st.rerun()

    if st.session_state.voice_turns:
        if st.button("↺ New Session", key="reset_voice", use_container_width=True):
            _reset_session()
            st.rerun()