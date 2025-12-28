import streamlit as st
import pandas as pd
import io
import time

# --- IMPORT LOCAL MODULES ---
from phase2_ingest import NeuralIngestor
from phase3_intent import CognitiveIntentEngine
from phase8_actions import ExecutionActionSuite
from phase5_schema import SchemaInferenceEngine
from phase6_materializer import DataMaterializer
from phase9_finalize import SchemaLockMaster

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Jeff Data Analyst",
    page_icon="🦇",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS STYLING (Blue Buttons Only) ---
# We kept ONLY the CSS for the blue buttons and resizing. No complex HTML cards.
st.markdown("""
<style>
    /* Background */
    .stApp { background-color: #0e1117; }
    
    /* Typography */
    h1, h2, h3, h4 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; letter-spacing: 1px; }
    p, label, .stMarkdown, .stTextInput, .stTextArea { font-family: 'Roboto', sans-serif !important; }
    .stDataFrame { font-family: 'Consolas', monospace !important; }
    
    /* Input Box Styling */
    textarea {
        font-family: 'Consolas', monospace !important;
        resize: vertical !important;
        min-height: 200px !important;
    }

    /* FORCE BLUE BUTTONS */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        background-color: #0e1117;
        color: #3b8ed0;
        border: 1px solid #3b8ed0;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #3b8ed0;
        color: white;
        border-color: #3b8ed0;
        box-shadow: 0 0 8px rgba(59, 142, 208, 0.4);
    }
    div.stButton > button:active {
        background-color: #2a6fa8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. INITIALIZE ENGINES ---
if 'ingestor' not in st.session_state:
    st.session_state.ingestor = NeuralIngestor()
    st.session_state.intent_engine = CognitiveIntentEngine()
    st.session_state.action_suite = ExecutionActionSuite()

# --- 4. SESSION STATE ---
if 'df' not in st.session_state: st.session_state.df = None
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'undo_stack' not in st.session_state: st.session_state.undo_stack = []

# --- 5. FUNCTIONS ---

def log_msg(sender, msg):
    timestamp = pd.Timestamp.now().strftime("%H:%M")
    icon = "🦇" if sender == "JEFF" else "👤" if sender == "USER" else "⚠️"
    entry = f"**{icon} [{timestamp}] {sender}:**\n\n{msg}\n\n---"
    st.session_state.chat_log.insert(0, entry)

def ingest_data():
    raw_text = st.session_state.get("raw_input_area", "")
    if not raw_text.strip():
        st.toast("Please paste data first.", icon="⚠️")
        return

    log_msg("JEFF", "Ingesting Data...")
    try:
        st.session_state.undo_stack = []
        df = st.session_state.ingestor.build_diagnostic_dataframe(raw_text)
        schema = SchemaInferenceEngine().infer(df)
        df = DataMaterializer().materialize(df, schema)
        df = SchemaLockMaster().lock(df, schema)
        
        st.session_state.df = df
        log_msg("JEFF", f"Data Materialized. {len(df)} rows found.")
        st.toast("Data Loaded Successfully", icon="✅")
    except Exception as e:
        log_msg("ERROR", str(e))
        st.error(f"Ingest Failed: {e}")

def run_command():
    cmd = st.session_state.get("cmd_input_box", "")
    if not cmd.strip(): return
    
    if st.session_state.df is None:
        st.toast("No data loaded.", icon="⚠️")
        return

    log_msg("USER", cmd)
    intent = st.session_state.intent_engine.analyze_command(cmd, st.session_state.df.columns)

    if intent["action"] == "unknown":
        suggestion = intent['suggestions'][0] if intent['suggestions'] else "Try 'Sort by Salary'"
        log_msg("JEFF", f"Unknown command. {suggestion}")
        return

    st.session_state.undo_stack.append(st.session_state.df.copy())

    try:
        if intent["action"] == "dedupe" and "subset" not in intent["parameters"]:
             intent["parameters"]["keep"] = "first"

        new_df, result_msg = st.session_state.action_suite.execute(intent, st.session_state.df)
        st.session_state.df = new_df
        log_msg("JEFF", result_msg)
        st.session_state["cmd_input_box"] = "" 
        
    except Exception as e:
        st.session_state.undo_stack.pop()
        log_msg("ERROR", str(e))

def undo_action():
    if st.session_state.undo_stack:
        st.session_state.df = st.session_state.undo_stack.pop()
        log_msg("JEFF", "Reverted to previous state.")
        st.toast("Undo Successful", icon="⏪")
    else:
        st.toast("Nothing to undo!", icon="🚫")

# --- 6. SIDEBAR LOG ---
with st.sidebar:
    st.header("📜 SESSION LOG")
    st.divider()
    for log_entry in st.session_state.chat_log:
        st.markdown(log_entry)

# --- 7. MAIN LAYOUT ---
st.title("🦇 JEFF DATA ANALYST")

col1, col2, col3, col4 = st.columns([1, 1, 1.2, 2.8], gap="small")

# === COL 1: INPUT ===
with col1:
    st.subheader("1. INPUT")
    st.text_area("Raw Data:", height=300, key="raw_input_area", placeholder="Paste Excel/CSV content here...", label_visibility="collapsed")
    st.button("⚡ INGEST", on_click=ingest_data)

# === COL 2: ACTIONS ===
with col2:
    st.subheader("2. ACTION")
    st.text_input("Command:", key="cmd_input_box", placeholder="Type here...", label_visibility="collapsed", on_change=run_command)
    st.button("▶ EXECUTE", on_click=run_command)
    st.button("⏪ UNDO LAST", on_click=undo_action)
    
    st.divider()
    
    # Safe Save Logic
    if st.session_state.df is not None:
        st.markdown("**💾 Save File**")
        fname = st.text_input("Filename:", value="analysis", label_visibility="collapsed")
        
        clean_df = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            clean_df.to_excel(writer, index=False)
            
        st.download_button(
            label="⬇️ DOWNLOAD",
            data=buffer,
            file_name=f"{fname}.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.button("💾 SAVE FILE", disabled=True)

# === COL 3: NEURAL GUIDE (NATIVE STREAMLIT) ===
# No HTML here. We use st.container with border=True to make "Cards"
with col3:
    st.subheader("3. GUIDE")
    
    with st.container(border=True):
        st.markdown("**🛠️ EDITING**")
        st.code("Update Salary to 5000 where ID is 1", language=None)
        st.code("Update Row 5 Name to Batman", language=None)

    with st.container(border=True):
        st.markdown("**🧹 CLEANING**")
        st.code("Fill missing in Age with 0", language=None)
        st.code("Replace 'NY' with 'New York'", language=None)
        st.code("Dedupe", language=None)

    with st.container(border=True):
        st.markdown("**🏷️ STRUCTURE**")
        st.code("Rename 'Old' to 'New'", language=None)
        st.code("Delete Row 5", language=None)

    with st.container(border=True):
        st.markdown("**📊 ANALYSIS**")
        st.code("Group by City sum Sales", language=None)
        st.code("Analyze Salary", language=None)
        st.code("Filter Age > 25", language=None)
        st.code("Plot Age", language=None)

# === COL 4: OUTPUT ===
with col4:
    if st.session_state.df is not None:
        clean_view = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        rows, cols = clean_view.shape
        st.success(f"**ACTIVE DATA:** {rows} Rows | {cols} Columns")
        st.dataframe(clean_view, height=750, use_container_width=True)
    else:
        st.warning("WAITING FOR DATA...")
        st.markdown("<br><br><center><h3 style='color:#555;'>NO DATA LOADED</h3></center>", unsafe_allow_html=True)
