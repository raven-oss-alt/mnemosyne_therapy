import streamlit as st
import sqlite3
import pandas as pd
import requests
import datetime
import json
from typing import List, Dict, Optional

# --- CONFIGURATION ---
DB_PATH = "mnemosyne_conversations.db"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Model options: llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
MODEL_NAME = "llama-3.1-70b-versatile"  # Using 70B for better therapeutic responses

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         started_at TEXT, 
         ended_at TEXT,
         session_type TEXT,
         patient_id TEXT,
         summary TEXT)''')
    
    # Conversation turns table
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversation_turns 
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         session_id INTEGER,
         timestamp TEXT,
         speaker TEXT,
         message TEXT,
         message_type TEXT,
         metadata TEXT,
         FOREIGN KEY(session_id) REFERENCES sessions(id))''')
    
    # Memory anchors table (for significant moments)
    cursor.execute('''CREATE TABLE IF NOT EXISTS memory_anchors 
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         session_id INTEGER,
         timestamp TEXT,
         category TEXT,
         original_text TEXT,
         reframed_text TEXT,
         emotional_valence REAL,
         FOREIGN KEY(session_id) REFERENCES sessions(id))''')
    
    conn.commit()
    conn.close()

def create_session(session_type: str, patient_id: str = "anonymous") -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO sessions (started_at, session_type, patient_id) VALUES (?, ?, ?)",
                (datetime.datetime.now().isoformat(), session_type, patient_id))
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id

def end_session(session_id: int, summary: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE sessions SET ended_at = ?, summary = ? WHERE id = ?",
                (datetime.datetime.now().isoformat(), summary, session_id))
    conn.commit()
    conn.close()

def save_turn(session_id: int, speaker: str, message: str, message_type: str = "dialogue", metadata: Dict = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO conversation_turns (session_id, timestamp, speaker, message, message_type, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, datetime.datetime.now().isoformat(), speaker, message, message_type, json.dumps(metadata or {})))
    conn.commit()
    conn.close()

def get_session_history(session_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT timestamp, speaker, message, message_type, metadata 
    FROM conversation_turns
    WHERE session_id = ?
    ORDER BY id ASC
    """
    df = pd.read_sql_query(query, conn, params=(session_id,))
    conn.close()
    return df.to_dict('records')

def save_memory_anchor(session_id: int, category: str, original: str, reframed: str, valence: float):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO memory_anchors (session_id, timestamp, category, original_text, reframed_text, emotional_valence) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, datetime.datetime.now().isoformat(), category, original, reframed, valence))
    conn.commit()
    conn.close()

def get_all_sessions() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT id, started_at, ended_at, session_type, patient_id, summary
    FROM sessions
    ORDER BY id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- THERAPEUTIC AI FRAMEWORKS ---

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

Common distortions to watch for:
- All-or-nothing thinking
- Overgeneralization
- Mental filter (focusing only on negatives)
- Catastrophizing
- Emotional reasoning
- Should statements
- Labeling

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
6. Ask about absent but implicit knowledge

Key questions:
- "When has this problem been less powerful?"
- "Who in your life would least be surprised by this strength?"
- "What does this say about what matters to you?"
- "If this problem had less influence, what would become possible?"

Be collaborative, curious, and respectful of the patient as the expert on their own life.""",
        "temperature": 0.7,
    },
    
    "exploratory_dialogue": {
        "system_prompt": """You are an empathetic conversational AI trained in person-centered therapy principles.

Your role is to:
1. Provide unconditional positive regard
2. Practice deep active listening and reflection
3. Help patients explore their experiences without judgment
4. Follow the patient's lead - they know what they need to talk about
5. Reflect feelings and content
6. Ask open-ended questions that deepen understanding
7. Trust the patient's capacity for self-direction

Core attitudes:
- Genuineness and authenticity
- Accurate empathy
- Unconditional positive regard
- Non-directiveness (mostly - offer gentle suggestions when helpful)

Create a warm, accepting presence where the patient feels truly heard.""",
        "temperature": 0.8,
    }
}

def build_conversation_context(history: List[Dict], max_turns: int = 10) -> List[Dict]:
    """Build conversation context from recent history in OpenAI format"""
    recent = history[-max_turns:] if len(history) > max_turns else history
    
    messages = []
    for turn in recent:
        if turn['speaker'] == 'PATIENT':
            messages.append({"role": "user", "content": turn['message']})
        elif turn['speaker'] == 'THERAPIST':
            messages.append({"role": "assistant", "content": turn['message']})
    
    return messages

def generate_ai_response(
    patient_message: str, 
    conversation_history: List[Dict],
    mode: str = "exploratory_dialogue",
    groq_api_key: str = None
) -> str:
    """Generate therapeutic AI response using Groq API"""
    
    if not groq_api_key:
        return "⚠️ API Key not configured. Please add your Groq API key in the sidebar."
    
    system_config = THERAPEUTIC_SYSTEMS.get(mode, THERAPEUTIC_SYSTEMS["exploratory_dialogue"])
    system_prompt = system_config["system_prompt"]
    temperature = system_config["temperature"]
    
    # Build messages array in OpenAI format
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    messages.extend(build_conversation_context(conversation_history))
    
    # Add current patient message
    messages.append({"role": "user", "content": patient_message})
    
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1000,
                "top_p": 1,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        elif response.status_code == 401:
            return "⚠️ Invalid API Key. Please check your Groq API key."
        elif response.status_code == 429:
            return "⚠️ Rate limit exceeded. Please wait a moment and try again."
        else:
            return f"⚠️ API Error (Status {response.status_code}): {response.text}"
            
    except requests.exceptions.Timeout:
        return "⚠️ Request timeout. Please try again."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def generate_session_summary(history: List[Dict], groq_api_key: str) -> str:
    """Generate an AI summary of the session using Groq"""
    
    if not history:
        return "No conversation occurred."
    
    if not groq_api_key:
        return "API key not configured."
    
    # Build full conversation
    conversation_text = "\n".join([f"{turn['speaker']}: {turn['message']}" for turn in history if turn['speaker'] in ['PATIENT', 'THERAPIST']])
    
    messages = [
        {"role": "system", "content": "You are a clinical supervisor reviewing therapy session notes."},
        {"role": "user", "content": f"""Review this therapeutic conversation and provide a brief clinical summary (3-4 sentences) covering:
1. Main themes discussed
2. Patient's emotional state/progress
3. Any insights or breakthroughs
4. Suggested focus for next session

Conversation:
{conversation_text}

Clinical Summary:"""}
    ]
    
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 300
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            return "Could not generate summary."
    except:
        return "Summary generation failed."

# --- STREAMLIT UI ---
st.set_page_config(
    page_title="Mnemosyne Conversational Therapeutic AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #e8eaed; }
    .stTextInput input, .stTextArea textarea { 
        background-color: #1e1e1e; 
        color: #e8eaed; 
        border: 1px solid #3d3d3d;
    }
    .patient-message {
        background-color: #1a472a;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #2ecc71;
    }
    .therapist-message {
        background-color: #1a3a52;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #3498db;
    }
    .system-message {
        background-color: #4a3a1a;
        padding: 8px;
        border-radius: 4px;
        margin: 6px 0;
        font-style: italic;
        font-size: 0.9em;
        border-left: 3px solid #f39c12;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE MANAGEMENT ---
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'session_history' not in st.session_state:
    st.session_state.session_history = []
if 'therapeutic_mode' not in st.session_state:
    st.session_state.therapeutic_mode = "exploratory_dialogue"
if 'groq_api_key' not in st.session_state:
    st.session_state.groq_api_key = ""

# --- HEADER ---
st.title("🏛️ Mnemosyne: Conversational Therapeutic AI")
st.caption("Research prototype for trauma processing and cognitive reframing | Powered by Groq")

# --- SIDEBAR: SESSION MANAGEMENT ---
with st.sidebar:
    st.header("🔑 API Configuration")
    
    # API Key input
    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        value=st.session_state.groq_api_key,
        help="Get your free API key at https://console.groq.com/keys"
    )
    
    if api_key_input != st.session_state.groq_api_key:
        st.session_state.groq_api_key = api_key_input
    
    if not st.session_state.groq_api_key:
        st.warning("⚠️ Enter your Groq API key to start")
        st.markdown("[Get Free API Key →](https://console.groq.com/keys)")
    else:
        st.success("✓ API Key configured")
    
    st.markdown("---")
    st.header("🎯 Session Control")
    
    # Session info
    if st.session_state.current_session_id:
        st.success(f"✓ Active Session #{st.session_state.current_session_id}")
        
        # Mode selector
        mode_labels = {
            "exploratory_dialogue": "🗣️ Exploratory Dialogue",
            "trauma_processing": "🧠 Trauma Processing",
            "cognitive_reframing": "🔄 Cognitive Reframing",
            "narrative_therapy": "📖 Narrative Therapy"
        }
        
        selected_mode = st.selectbox(
            "Therapeutic Mode",
            options=list(mode_labels.keys()),
            format_func=lambda x: mode_labels[x],
            index=list(mode_labels.keys()).index(st.session_state.therapeutic_mode)
        )
        
        if selected_mode != st.session_state.therapeutic_mode:
            st.session_state.therapeutic_mode = selected_mode
            save_turn(
                st.session_state.current_session_id,
                "SYSTEM",
                f"Therapeutic mode changed to: {mode_labels[selected_mode]}",
                "mode_change"
            )
            st.rerun()
        
        st.markdown("---")
        
        # End session button
        if st.button("🛑 End Session", use_container_width=True):
            summary = generate_session_summary(st.session_state.session_history, st.session_state.groq_api_key)
            end_session(st.session_state.current_session_id, summary)
            st.session_state.current_session_id = None
            st.session_state.session_history = []
            st.rerun()
            
    else:
        st.info("No active session")
        
        # Start new session
        session_type = st.selectbox(
            "Session Type",
            ["Initial Assessment", "Trauma Processing", "Follow-up", "Crisis Support", "General Therapy"]
        )
        
        patient_id = st.text_input("Patient ID (optional)", value="anonymous")
        
        if st.button("▶️ Start New Session", use_container_width=True, disabled=not st.session_state.groq_api_key):
            session_id = create_session(session_type, patient_id)
            st.session_state.current_session_id = session_id
            st.session_state.session_history = []
            st.session_state.therapeutic_mode = "exploratory_dialogue"
            
            # Save opening
            save_turn(session_id, "SYSTEM", f"Session started: {session_type}", "session_start")
            save_turn(
                session_id,
                "THERAPIST",
                "Hello, I'm here to listen and support you. This is a safe space to explore whatever is on your mind. What would you like to talk about today?",
                "greeting"
            )
            st.rerun()
    
    st.markdown("---")
    
    # Session history browser
    st.subheader("📚 Past Sessions")
    all_sessions = get_all_sessions()
    
    if not all_sessions.empty:
        for _, session in all_sessions.head(5).iterrows():
            status = "✓" if session['ended_at'] else "⏸"
            with st.expander(f"{status} Session #{session['id']} - {session['session_type']}", expanded=False):
                st.caption(f"Started: {session['started_at'][:16]}")
                if session['ended_at']:
                    st.caption(f"Ended: {session['ended_at'][:16]}")
                if session['summary']:
                    st.write(session['summary'])
                
                if st.button(f"Load Session #{session['id']}", key=f"load_{session['id']}"):
                    st.session_state.current_session_id = int(session['id'])
                    st.session_state.session_history = get_session_history(int(session['id']))
                    st.rerun()

# --- MAIN CONVERSATION AREA ---
if st.session_state.current_session_id:
    
    # Display conversation history
    st.markdown("### 💬 Conversation")
    
    # Reload history from DB to ensure consistency
    if not st.session_state.session_history:
        st.session_state.session_history = get_session_history(st.session_state.current_session_id)
    
    # Display all turns
    for turn in st.session_state.session_history:
        speaker = turn['speaker']
        message = turn['message']
        msg_type = turn['message_type']
        
        if speaker == "PATIENT":
            st.markdown(f'<div class="patient-message"><strong>Patient:</strong><br>{message}</div>', unsafe_allow_html=True)
        elif speaker == "THERAPIST":
            st.markdown(f'<div class="therapist-message"><strong>Therapist:</strong><br>{message}</div>', unsafe_allow_html=True)
        elif speaker == "SYSTEM":
            st.markdown(f'<div class="system-message">🔔 {message}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Input area
    col1, col2 = st.columns([5, 1])
    
    with col1:
        patient_input = st.text_area(
            "Your response:",
            height=120,
            key="patient_input",
            placeholder="Share your thoughts, feelings, or experiences here...",
            disabled=not st.session_state.groq_api_key
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")
        send_button = st.button("📤 Send", use_container_width=True, type="primary", disabled=not st.session_state.groq_api_key)
    
    if send_button and patient_input.strip():
        # Save patient turn
        save_turn(st.session_state.current_session_id, "PATIENT", patient_input.strip(), "dialogue")
        st.session_state.session_history.append({
            'speaker': 'PATIENT',
            'message': patient_input.strip(),
            'message_type': 'dialogue',
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Generate AI response
        with st.spinner("Therapist is responding..."):
            ai_response = generate_ai_response(
                patient_input.strip(),
                st.session_state.session_history,
                mode=st.session_state.therapeutic_mode,
                groq_api_key=st.session_state.groq_api_key
            )
        
        # Save therapist turn
        save_turn(st.session_state.current_session_id, "THERAPIST", ai_response, "dialogue")
        st.session_state.session_history.append({
            'speaker': 'THERAPIST',
            'message': ai_response,
            'message_type': 'dialogue',
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        st.rerun()
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("📊 Generate Progress Summary", disabled=not st.session_state.groq_api_key):
            with st.spinner("Analyzing session..."):
                summary = generate_session_summary(st.session_state.session_history, st.session_state.groq_api_key)
                st.info(summary)
    
    with action_col2:
        if st.button("🔄 Clear Chat Display"):
            st.session_state.session_history = []
            st.rerun()
    
    with action_col3:
        if st.button("💾 Export Session Data"):
            if st.session_state.session_history:
                export_data = {
                    "session_id": st.session_state.current_session_id,
                    "history": st.session_state.session_history
                }
                st.download_button(
                    "⬇️ Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"session_{st.session_state.current_session_id}.json",
                    mime="application/json"
                )

else:
    # No active session
    st.info("👈 Configure your API key and start a session from the sidebar to begin.")
    
    st.markdown("### 🎓 About Mnemosyne")
    st.markdown("""
    This conversational AI system is designed for research in therapeutic dialogue and trauma processing.
    
    **Features:**
    - **Session-based conversations** with full context retention
    - **Multiple therapeutic modalities**: Exploratory dialogue, trauma processing, CBT, narrative therapy
    - **Powered by Groq API** - Fast, free tier available, using Llama 3.1 models
    - **Full conversation history** stored in SQLite database
    - **Session summaries** generated by AI
    - **Export functionality** for research data
    
    **Getting Started:**
    1. Get a free Groq API key at [console.groq.com/keys](https://console.groq.com/keys)
    2. Enter your API key in the sidebar
    3. Start a new session
    4. Begin conversing!
    
    **Research Use Only**: This tool is for research purposes. For clinical deployment, ensure proper licensing, 
    supervision by licensed professionals, and compliance with relevant healthcare regulations.
    
    **Privacy Note**: All conversations are stored locally in the database. In deployed versions, ensure 
    appropriate data protection measures.
    """)
    
    st.markdown("### 🚀 How to Get Your Free Groq API Key")
    st.markdown("""
    1. Visit [console.groq.com](https://console.groq.com)
    2. Sign up for a free account
    3. Go to "API Keys" section
    4. Click "Create API Key"
    5. Copy the key and paste it in the sidebar
    
    **Free tier includes:**
    - 30 requests/minute
    - 14,400 requests/day
    - Perfect for research testing!
    """)

st.markdown("---")
st.caption(f"🔧 Engine: {MODEL_NAME} (Groq) | 💾 Database: {DB_PATH}")