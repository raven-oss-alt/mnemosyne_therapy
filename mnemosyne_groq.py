import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import requests
import datetime
import json
from typing import List, Dict

# --- CONFIGURATION ---
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"

# --- API KEY LOADER ---
def get_api_key():
    try:
        key = st.secrets["GROQ_API_KEY"]
        if key and key.strip():
            return key.strip()
    except Exception:
        pass
    return st.session_state.get("groq_api_key", "")

# --- POSTGRESQL CONNECTION ---
def get_db_connection():
    """Get PostgreSQL connection from secrets"""
    try:
        return psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"]
        )
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# --- DATABASE INIT ---
def init_db():
    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            session_type TEXT,
            patient_id TEXT,
            summary TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS conversation_turns (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES sessions(id),
            timestamp TIMESTAMP,
            speaker TEXT,
            message TEXT,
            message_type TEXT,
            metadata TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS memory_anchors (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES sessions(id),
            timestamp TIMESTAMP,
            category TEXT,
            original_text TEXT,
            reframed_text TEXT,
            emotional_valence REAL
        )''')
        conn.commit()
    except Exception as e:
        st.error(f"Database init failed: {e}")
    finally:
        conn.close()

def create_session(session_type, patient_id="anonymous"):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO sessions (started_at, session_type, patient_id) VALUES (%s, %s, %s) RETURNING id",
                    (datetime.datetime.now(), session_type, patient_id))
        sid = cur.fetchone()[0]
        conn.commit()
        return sid
    except Exception as e:
        st.error(f"Session creation failed: {e}")
        return None
    finally:
        conn.close()

def end_session(session_id, summary):
    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("UPDATE sessions SET ended_at = %s, summary = %s WHERE id = %s",
                    (datetime.datetime.now(), summary, session_id))
        conn.commit()
    finally:
        conn.close()

def save_turn(session_id, speaker, message, message_type="dialogue", metadata=None):
    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO conversation_turns (session_id, timestamp, speaker, message, message_type, metadata) VALUES (%s, %s, %s, %s, %s, %s)",
                    (session_id, datetime.datetime.now(), speaker, message, message_type, json.dumps(metadata or {})))
        conn.commit()
    finally:
        conn.close()

def get_session_history(session_id):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT timestamp, speaker, message, message_type, metadata FROM conversation_turns WHERE session_id = %s ORDER BY id ASC", (session_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_all_sessions():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    try:
        df = pd.read_sql_query("SELECT id, started_at, ended_at, session_type, patient_id, summary FROM sessions ORDER BY id DESC", conn)
        return df
    finally:
        conn.close()

# --- SESSION IMPORT ---
def import_session_from_json(json_data):
    """Import a session from exported JSON file"""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        history = json_data.get("history", [])
        if not history:
            return None
        
        # Create new session
        cur = conn.cursor()
        first_turn = history[0]
        session_type = first_turn.get("message", "").replace("Session started: ", "") if first_turn.get("speaker") == "SYSTEM" else "Imported Session"
        
        cur.execute("INSERT INTO sessions (started_at, session_type, patient_id) VALUES (%s, %s, %s) RETURNING id",
                    (datetime.datetime.now(), session_type, "imported"))
        new_session_id = cur.fetchone()[0]
        
        # Import all turns
        for turn in history:
            cur.execute("INSERT INTO conversation_turns (session_id, timestamp, speaker, message, message_type, metadata) VALUES (%s, %s, %s, %s, %s, %s)",
                        (new_session_id, turn.get("timestamp", datetime.datetime.now()), turn["speaker"], turn["message"], turn.get("message_type", "dialogue"), turn.get("metadata", "{}")))
        
        conn.commit()
        return new_session_id
    except Exception as e:
        st.error(f"Import failed: {e}")
        return None
    finally:
        conn.close()

# --- THERAPEUTIC SYSTEMS ---
THERAPEUTIC_SYSTEMS = {
    "trauma_processing": {
        "system_prompt": """You are a trauma-informed therapeutic AI assistant trained in EMDR and narrative therapy principles.
Your role is to:
1. Create a safe, non-judgmental space for exploring difficult memories
2. Help the patient externalize and observe traumatic experiences from a third-person perspective
3. Use bilateral stimulation metaphors (past/present, observer/experiencer)
4. Never minimize suffering, but help create cognitive distance
5. Identify moments of resilience and agency within difficult narratives
6. Use gentle, paced questioning - never rush or pressure
Key techniques:
- Pendulation: Move between difficult content and resources/safety
- Titration: Process small amounts of traumatic material at a time
- Dual awareness: "Part of you experienced this, and part of you is safe here now"
- Witnessing stance: "What do you notice about that younger version of yourself?"
Respond with empathy, clinical precision, and respect for the patient's autonomy.""",
        "temperature": 0.7,
    },
    "cognitive_reframing": {
        "system_prompt": """You are a cognitive-behavioral therapy (CBT) assistant specializing in cognitive restructuring.
Your role is to:
1. Help identify automatic negative thoughts and cognitive distortions
2. Guide patients to examine evidence for and against their beliefs
3. Develop more balanced, realistic alternative perspectives
4. Never invalidate feelings, but question thoughts
5. Use Socratic questioning to promote self-discovery
Common distortions to watch for: All-or-nothing thinking, Overgeneralization, Mental filter, Catastrophizing, Emotional reasoning, Should statements, Labeling
Ask clarifying questions and help the patient become a scientist of their own thoughts.""",
        "temperature": 0.6,
    },
    "narrative_therapy": {
        "system_prompt": """You are a narrative therapy specialist who helps people re-author their life stories.
Your role is to:
1. Help externalize problems ("the anxiety" not "you are anxious")
2. Identify unique outcomes - times when the problem didn't dominate
3. Thicken alternative storylines of strength and agency
4. Explore preferred identities and values
5. Use curious, non-expert positioning
Key questions: "When has this problem been less powerful?", "Who in your life would least be surprised by this strength?", "What does this say about what matters to you?"
Be collaborative, curious, and respectful of the patient as the expert on their own life.""",
        "temperature": 0.7,
    },
    "exploratory_dialogue": {
        "system_prompt": """You are an empathetic conversational AI trained in person-centered therapy principles.
Your role is to:
1. Provide unconditional positive regard
2. Practice deep active listening and reflection
3. Help patients explore their experiences without judgment
4. Follow the patient's lead
5. Ask open-ended questions that deepen understanding
6. Trust the patient's capacity for self-direction
Create a warm, accepting presence where the patient feels truly heard.""",
        "temperature": 0.8,
    }
}

def build_context(history, max_turns=10):
    recent = history[-max_turns:] if len(history) > max_turns else history
    messages = []
    for turn in recent:
        if turn['speaker'] == 'PATIENT':
            messages.append({"role": "user", "content": turn['message']})
        elif turn['speaker'] == 'THERAPIST':
            messages.append({"role": "assistant", "content": turn['message']})
    return messages

def generate_ai_response(patient_message, history, mode="exploratory_dialogue", groq_api_key=None):
    if not groq_api_key:
        return "⚠️ API Key not configured."
    system_config = THERAPEUTIC_SYSTEMS.get(mode, THERAPEUTIC_SYSTEMS["exploratory_dialogue"])
    messages = [{"role": "system", "content": system_config["system_prompt"]}]
    messages.extend(build_context(history))
    messages.append({"role": "user", "content": patient_message})
    try:
        response = requests.post(GROQ_API_URL, headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}, json={"model": MODEL_NAME, "messages": messages, "temperature": system_config["temperature"], "max_tokens": 1000, "stream": False}, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        elif response.status_code == 401:
            return "⚠️ Invalid API Key."
        elif response.status_code == 429:
            return "⚠️ Rate limit exceeded. Please wait and try again."
        else:
            return f"⚠️ API Error ({response.status_code})"
    except requests.exceptions.Timeout:
        return "⚠️ Request timeout. Please try again."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def generate_summary(history, groq_api_key):
    if not history or not groq_api_key:
        return "No conversation to summarize."
    conversation_text = "\n".join([f"{t['speaker']}: {t['message']}" for t in history if t['speaker'] in ['PATIENT', 'THERAPIST']])
    messages = [{"role": "system", "content": "You are a clinical supervisor reviewing therapy session notes."}, {"role": "user", "content": f"Summarize this therapy session in 3-4 sentences covering: main themes, patient emotional state, any breakthroughs, and suggested next session focus.\n\nConversation:\n{conversation_text}\n\nClinical Summary:"}]
    try:
        response = requests.post(GROQ_API_URL, headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}, json={"model": MODEL_NAME, "messages": messages, "temperature": 0.5, "max_tokens": 300}, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        return "Could not generate summary."
    except:
        return "Summary generation failed."

# --- STREAMLIT UI ---
st.set_page_config(page_title="Mnemosyne Therapeutic AI", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #e8eaed; }
    .stTextInput input, .stTextArea textarea { background-color: #1e1e1e; color: #e8eaed; border: 1px solid #3d3d3d; }
    .patient-message { background-color: #1a472a; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #2ecc71; }
    .therapist-message { background-color: #1a3a52; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #3498db; }
    .system-message { background-color: #4a3a1a; padding: 8px; border-radius: 4px; margin: 6px 0; font-style: italic; font-size: 0.9em; border-left: 3px solid #f39c12; }
    </style>
""", unsafe_allow_html=True)

# Session state init
for key, val in [('current_session_id', None), ('session_history', []), ('therapeutic_mode', 'exploratory_dialogue'), ('groq_api_key', '')]:
    if key not in st.session_state:
        st.session_state[key] = val

st.title("🏛️ Mnemosyne: Conversational Therapeutic AI")
st.caption("Research prototype for trauma processing and cognitive reframing | Powered by Groq + PostgreSQL")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 API Configuration")
    GROQ_API_KEY = get_api_key()

    if GROQ_API_KEY:
        st.success("✓ API Key configured")
    else:
        manual_key = st.text_input("Groq API Key", type="password", value=st.session_state.groq_api_key, help="Get your free key at https://console.groq.com/keys")
        if manual_key:
            st.session_state.groq_api_key = manual_key
            GROQ_API_KEY = manual_key
            st.success("✓ API Key entered")
        else:
            st.warning("⚠️ Enter your Groq API key to start")

    st.markdown("---")
    st.header("📥 Import Session")
    uploaded_file = st.file_uploader("Upload session JSON", type=['json'])
    if uploaded_file:
        try:
            json_data = json.load(uploaded_file)
            if st.button("📂 Import & Continue Session"):
                imported_id = import_session_from_json(json_data)
                if imported_id:
                    st.session_state.current_session_id = imported_id
                    st.session_state.session_history = get_session_history(imported_id)
                    st.success(f"✓ Session imported! Session #{imported_id}")
                    st.rerun()
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

    st.markdown("---")
    st.header("🎯 Session Control")

    if st.session_state.current_session_id:
        st.success(f"✓ Active Session #{st.session_state.current_session_id}")

        mode_labels = {
            "exploratory_dialogue": "🗣️ Exploratory Dialogue",
            "trauma_processing": "🧠 Trauma Processing",
            "cognitive_reframing": "🔄 Cognitive Reframing",
            "narrative_therapy": "📖 Narrative Therapy"
        }

        selected_mode = st.selectbox("Therapeutic Mode", options=list(mode_labels.keys()), format_func=lambda x: mode_labels[x], index=list(mode_labels.keys()).index(st.session_state.therapeutic_mode))

        if selected_mode != st.session_state.therapeutic_mode:
            st.session_state.therapeutic_mode = selected_mode
            save_turn(st.session_state.current_session_id, "SYSTEM", f"Mode changed to: {mode_labels[selected_mode]}", "mode_change")
            st.rerun()

        st.markdown("---")

        if st.button("🛑 End Session", use_container_width=True):
            summary = generate_summary(st.session_state.session_history, GROQ_API_KEY)
            end_session(st.session_state.current_session_id, summary)
            st.session_state.current_session_id = None
            st.session_state.session_history = []
            st.rerun()
    else:
        st.info("No active session")
        session_type = st.selectbox("Session Type", ["Initial Assessment", "Trauma Processing", "Follow-up", "Crisis Support", "General Therapy"])
        patient_id = st.text_input("Patient ID (optional)", value="anonymous")

        if st.button("▶️ Start New Session", use_container_width=True, disabled=not GROQ_API_KEY):
            sid = create_session(session_type, patient_id)
            if sid:
                st.session_state.current_session_id = sid
                st.session_state.session_history = []
                st.session_state.therapeutic_mode = "exploratory_dialogue"
                save_turn(sid, "SYSTEM", f"Session started: {session_type}", "session_start")
                save_turn(sid, "THERAPIST", "Hello, I'm here to listen and support you. This is a safe space to explore whatever is on your mind. What would you like to talk about today?", "greeting")
                st.rerun()

    st.markdown("---")
    st.subheader("📚 Past Sessions")
    all_sessions = get_all_sessions()

    if not all_sessions.empty:
        for _, session in all_sessions.head(5).iterrows():
            status = "✓" if pd.notna(session['ended_at']) else "⏸"
            with st.expander(f"{status} Session #{session['id']} - {session['session_type']}", expanded=False):
                st.caption(f"Started: {str(session['started_at'])[:16]}")
                if pd.notna(session['ended_at']):
                    st.caption(f"Ended: {str(session['ended_at'])[:16]}")
                if pd.notna(session['summary']):
                    st.write(session['summary'])
                if st.button(f"Load Session #{session['id']}", key=f"load_{session['id']}"):
                    st.session_state.current_session_id = int(session['id'])
                    st.session_state.session_history = get_session_history(int(session['id']))
                    st.rerun()

# --- MAIN AREA ---
if st.session_state.current_session_id:
    st.markdown("### 💬 Conversation")

    if not st.session_state.session_history:
        st.session_state.session_history = get_session_history(st.session_state.current_session_id)

    for turn in st.session_state.session_history:
        if turn['speaker'] == "PATIENT":
            st.markdown(f'<div class="patient-message"><strong>Patient:</strong><br>{turn["message"]}</div>', unsafe_allow_html=True)
        elif turn['speaker'] == "THERAPIST":
            st.markdown(f'<div class="therapist-message"><strong>Therapist:</strong><br>{turn["message"]}</div>', unsafe_allow_html=True)
        elif turn['speaker'] == "SYSTEM":
            st.markdown(f'<div class="system-message">🔔 {turn["message"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([5, 1])
    with col1:
        patient_input = st.text_area("Your response:", height=120, key="patient_input", placeholder="Share your thoughts, feelings, or experiences here...", disabled=not GROQ_API_KEY)
    with col2:
        st.write("")
        st.write("")
        send_button = st.button("📤 Send", use_container_width=True, type="primary", disabled=not GROQ_API_KEY)

    if send_button and patient_input.strip():
        # Check for session end keywords
        input_lower = patient_input.strip().lower()
        end_keywords = ["//end", "//close", "//finish", "//done"]
        
        if any(keyword in input_lower for keyword in end_keywords):
            # End session gracefully
            save_turn(st.session_state.current_session_id, "PATIENT", patient_input.strip(), "dialogue")
            save_turn(st.session_state.current_session_id, "SYSTEM", "Session ended by patient using keyword command", "session_end")
            summary = generate_summary(st.session_state.session_history, GROQ_API_KEY)
            end_session(st.session_state.current_session_id, summary)
            st.success("✓ Session ended successfully!")
            st.session_state.current_session_id = None
            st.session_state.session_history = []
            st.rerun()
        else:
            # Normal conversation flow
            save_turn(st.session_state.current_session_id, "PATIENT", patient_input.strip(), "dialogue")
            st.session_state.session_history.append({'speaker': 'PATIENT', 'message': patient_input.strip(), 'message_type': 'dialogue', 'timestamp': datetime.datetime.now()})
            with st.spinner("Therapist is responding..."):
                ai_response = generate_ai_response(patient_input.strip(), st.session_state.session_history, mode=st.session_state.therapeutic_mode, groq_api_key=GROQ_API_KEY)
            save_turn(st.session_state.current_session_id, "THERAPIST", ai_response, "dialogue")
            st.session_state.session_history.append({'speaker': 'THERAPIST', 'message': ai_response, 'message_type': 'dialogue', 'timestamp': datetime.datetime.now()})
            st.rerun()

    st.markdown("### ⚡ Quick Actions")
    a1, a2, a3 = st.columns(3)

    with a1:
        if st.button("📊 Generate Progress Summary", disabled=not GROQ_API_KEY):
            with st.spinner("Analyzing session..."):
                st.info(generate_summary(st.session_state.session_history, GROQ_API_KEY))

    with a2:
        if st.button("🔄 Clear Chat Display"):
            st.session_state.session_history = []
            st.rerun()

    with a3:
        if st.button("💾 Export Session Data"):
            if st.session_state.session_history:
                export_data = {"session_id": st.session_state.current_session_id, "history": st.session_state.session_history}
                st.download_button("⬇️ Download JSON", data=json.dumps(export_data, indent=2, default=str), file_name=f"session_{st.session_state.current_session_id}.json", mime="application/json")
else:
    st.info("👈 Start a session or import your previous session from the sidebar")
    st.markdown("""
### 🎓 About Mnemosyne + PostgreSQL
**New Features:**
- ✅ **Permanent session storage** - Sessions survive app restarts
- ✅ **Import past sessions** - Continue where you left off
- ✅ **Cloud database** - Data persists forever
- ✅ **Quick end keywords** - Type `//end`, `//close`, `//finish`, or `//done` to end session instantly

**Getting Started:**
1. Upload your previous session JSON in the sidebar
2. Click "Import & Continue Session"
3. Keep chatting from where you left off!

**Quick Commands:**
- Type `//end` in chat to end session without clicking button
- Session auto-saves and generates summary
- Works in any message

**Research Use Only**: Ensure proper licensing and supervision for clinical deployment.
""")

st.markdown("---")
st.caption(f"🔧 Engine: {MODEL_NAME} (Groq) | 💾 Database: PostgreSQL (Persistent)")
