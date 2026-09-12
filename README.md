# Kivi Connected

## How to Run

**Requirements:** Python 3.11+

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the app:
   ```bash
   streamlit run src/main.py
   ```
3. Open the local URL Streamlit prints (typically `http://localhost:8501`).
4. Sign up / log in.
5. In the sidebar, paste a Sarvam API key and click "Save Key" (get one from [indus.sarvam.ai](https://indus.sarvam.ai)).
6. Go to the "Conversations" tab and try:
   - Recording a mic message asking Kivi to remember something (e.g. "remember my favorite color is blue").
   - Asking a follow-up question that depends on that memory (e.g. "what's my favorite color?").
   - Clicking "New Session" to confirm state resets cleanly.

No environment variables or `.env` file are required — the Sarvam API key is entered per-user inside the app and stored in the local SQLite database. The SQLite file (`users.db`) and the Chroma vector store (`chroma_db/`) are created automatically on first run.

To reset the system entirely: delete `users.db` and the `chroma_db/` directory, then restart the app.

---

## Product Overview

Kivi is a voice-first assistant with two modes:

- **Dictation** — the user speaks and Kivi transcribes/formats it as text.
- **Hey Kivi (Conversations)** — the user talks to Kivi directly and gets a spoken reply, with access to semantic memory: facts the user has explicitly asked Kivi to remember, retrieved via a vector store and injected into the model's context on each turn.

## Architecture

- **Frontend:** Streamlit, tabbed interface (`Dictations` / `Conversations`), chat-bubble UI for the voice conversation.
- **Speech:** SarvamAI APIs for speech-to-text (`saaras:v3`), the conversational LLM (`sarvam-105b-conversations`), and text-to-speech (`bulbul:v3`).
- **Storage:**
  - SQLite (`users.db`) — user accounts, dictation history, voice history, and the `memory` table (structured record of saved facts).
  - Chroma (`chroma_db/`) — vector embeddings of saved memories, one collection per user, used for semantic retrieval at query time.
- **Memory-save flow:** each Hey Kivi turn asks the model to return structured JSON (`{"answer": ..., "memory_to_save": ...}`). When `memory_to_save` is non-null, the fact is written to both the SQL `memory` table and the Chroma store in the same step, keyed by the same ID.

## Use Cases

- Ask Kivi to remember a fact in conversation ("remember my flight is at 5 PM") and recall it later.
- Update a previously stored fact by simply stating the new value (e.g. correcting a changed flight time) — Kivi is instructed to treat new statements as authoritative, not to keep asserting stale memory.
- General conversational Q&A, using the model's own knowledge when a question isn't personal.

## Limitations

- Memory-save detection depends on the LLM correctly recognizing an explicit "remember this" intent inside a single combined call; it is not a hard rule-based trigger, so it can occasionally miss or misfire.
- No editing/deleting of individual saved memories from the UI yet.
- No dedicated evaluation harness or generated test corpus yet.
- Chroma similarity search may occasionally surface a loosely related memory rather than the most relevant one for very short/ambiguous queries.

## AI Disclosure

The product position and vision (Part One) reflect my own thinking and were not generated or drafted by AI. AI assistance was used for:
- Debugging (e.g. diagnosing why saved memories weren't persisting, and a JSON-parsing bug in the model's structured output).
- Front-end/interface code (restyling the conversation view into a chat-message layout).
- Spelling and grammar review of the Part One documents (content and reasoning are my own).
- This README file itself was formatted by AI.