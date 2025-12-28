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
    initial_sidebar_state="collapsed" # This hides the Session Log menu by default
)

# --- 2. CSS STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; letter-spacing: 1px; }
    .stTextInput, .stTextArea, .stButton { font-family: 'Roboto', sans-serif !important; }
    .stDataFrame { font-family: 'Consolas', monospace !important; }
    
    /* Button Styling */
    div.stButton > button {
        width: 100%;
        border-radius: 4px;
        font-weight: bold;
        border: 1px solid #3b8ed0;
    }
    div.stButton > button:hover {
        border-color: white;
        color: #3b8ed0;
    }
    
    /* Success/Error Messages */
    .stToast { font-family: 'Roboto', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. INITIALIZE ENGINES ---
if 'engines_loaded' not in st.session_state:
    st.session_state.ingestor = NeuralIngestor()
    st.session_state.intent_engine = CognitiveIntentEngine()
    st.session_state.action_suite = ExecutionActionSuite()
    st.session_state.engines_loaded = True

# --- 4. SESSION STATE ---
if 'df' not in st.session_state: st.session_state.df = None
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'undo_stack' not in st.session_state: st.session_state.undo_stack = []

# --- 5. FUNCTIONS ---

def log_msg(sender, msg, type="info"):
    timestamp = pd.Timestamp.now().strftime("%H:%M")
    icon = "🦇" if sender == "JEFF" else "👤" if sender == "USER" else "⚠️"
    color = "#3b8ed0" if sender == "JEFF" else "#2ecc71" if sender == "USER" else "#e74c3c"
    
    # Simple markdown log for the sidebar
    entry = f"**{icon} [{timestamp}] {sender}:**\n\n{msg}\n\n---"
    st.session_state.chat_log.insert(0, entry)

def undo_action():
    if st.session_state.undo_stack:
        st.session_state.df = st.session_state.undo_stack.pop()
        log_msg("JEFF", "Reverted to previous state.")
        st.toast("Undo Successful", icon="⏪")
    else:
        st.toast("Nothing to undo!", icon="🚫")

def ingest_data():
    raw_text = st.session_state.raw_input_area
    if not raw_text.strip():
        st.toast("Paste data first.", icon="⚠️")
        return

    log_msg("JEFF", "Ingesting Data...")
    try:
        st.session_state.undo_stack = []
        df = st.session_state.ingestor.build_diagnostic_dataframe(raw_text)
        schema = SchemaInferenceEngine().infer(df)
        df = DataMaterializer().materialize(df, schema)
        df = SchemaLockMaster().lock(df, schema)
        
        st.session_state.df = df
        log_msg("JEFF", f"Data Materialized. {len(df)} rows.")
        st.toast("Data Loaded Successfully", icon="✅")
    except Exception as e:
        log_msg("ERROR", str(e))
        st.error(f"Ingest Failed: {e}")

def run_command():
    cmd = st.session_state.cmd_input_box
    if not cmd.strip(): return
    
    if st.session_state.df is None:
        st.toast("No data loaded.", icon="⚠️")
        return

    log_msg("USER", cmd)
    intent = st.session_state.intent_engine.analyze_command(cmd, st.session_state.df.columns)

    if intent["action"] == "unknown":
        suggestion = intent['suggestions'][0] if intent['suggestions'] else "Try 'Sort by Salary'"
        log_msg("JEFF", f"Unknown command. {suggestion}")
        st.toast("Unknown Command", icon="❓")
        return

    st.session_state.undo_stack.append(st.session_state.df.copy())

    try:
        if intent["action"] == "dedupe" and "subset" not in intent["parameters"]:
             intent["parameters"]["keep"] = "first"

        new_df, result_msg = st.session_state.action_suite.execute(intent, st.session_state.df)
        st.session_state.df = new_df
        log_msg("JEFF", result_msg)
        st.session_state.cmd_input_box = "" 
        
    except Exception as e:
        st.session_state.undo_stack.pop()
        log_msg("ERROR", str(e))
        st.toast("Execution Failed", icon="❌")

# --- 6. SIDEBAR (THE "MENU" BUTTON) ---
with st.sidebar:
    st.header("📜 SESSION LOG")
    st.markdown("Here is the history of your current analysis session.")
    st.divider()
    # Display logs in the sidebar menu
    for log_entry in st.session_state.chat_log:
        st.markdown(log_entry)

# --- 7. MAIN LAYOUT (TRI-COLUMN) ---
st.title("🦇 JEFF DATA ANALYST")

# Define Columns: Input (1) | Command (1) | Output (2)
col_input, col_cmd, col_output = st.columns([1, 1, 2], gap="medium")

# === COLUMN 1: INPUT DECK ===
with col_input:
    st.subheader("1. SOURCE")
    st.text_area(
        "Raw Data Input:", 
        height=300, 
        key="raw_input_area",
        placeholder="Copy from Excel/CSV and paste here...",
        label_visibility="collapsed"
    )
    st.button("⚡ INGEST DATA", on_click=ingest_data, type="primary")
    
    st.info("ℹ️ **Tip:** Paste raw data including headers. Jeff will auto-detect the structure.")

# === COLUMN 2: COMMAND CENTER ===
with col_cmd:
    st.subheader("2. ACTIONS")
    
    # Command Input
    st.text_input(
        "Command:", 
        key="cmd_input_box", 
        placeholder="Type command here...",
        label_visibility="collapsed",
        on_change=run_command
    )
    
    # Action Buttons
    c1, c2 = st.columns(2)
    with c1: st.button("▶ EXECUTE", on_click=run_command)
    with c2: st.button("⏪ UNDO", on_click=undo_action)
    
    if st.session_state.df is not None:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.df.to_excel(writer, index=False)
        st.download_button("💾 DOWNLOAD", data=buffer, file_name="analysis.xlsx", mime="application/vnd.ms-excel")
    else:
        st.button("💾 DOWNLOAD", disabled=True)

    st.divider()

    # Detailed Cheat Sheet
    st.markdown("#### 🧠 NEURAL GUIDE")
    
    with st.expander("🛠️ EDITING & CLEANING", expanded=True):
        st.markdown("""
        **Update Values:**
        * `Update Salary to 5000 where ID is 1`
        * `Update Row 5 Name to Batman`
        
        **Cleaning:**
        * `Fill missing in Age with 0`
        * `Replace 'NY' with 'New York'`
        * `Dedupe` (Removes duplicates)
        
        **Structure:**
        * `Rename 'Old' to 'New'`
        * `Delete Row 5`
        * `Delete Column 'Tax'`
        """)
        
    with st.expander("📊 ANALYSIS & VISUALS", expanded=True):
        st.markdown("""
        **Pivot / Grouping:**
        * `Group by City sum Sales`
        * `Group by Dept count ID`
        
        **Statistics:**
        * `Analyze Salary` (Mean, Max, Min)
        
        **Sorting & Filtering:**
        * `Sort by Date Desc`
        * `Filter Age > 25`
        
        **Charts:**
        * `Plot Age` (Histogram/Bar)
        """)

# === COLUMN 3: LIVE OUTPUT ===
with col_output:
    if st.session_state.df is not None:
        rows, cols = st.session_state.df.shape
        st.success(f"**STATUS: ACTIVE** | {rows} Rows | {cols} Columns")
        st.dataframe(st.session_state.df, height=750, use_container_width=True)
    else:
        st.warning("WAITING FOR DATA...")
        st.markdown("""
        <div style='text-align: center; color: #555; padding-top: 100px;'>
            <h3>NO DATA LOADED</h3>
            <p>Paste data in Column 1 to begin.</p>
        </div>
        """, unsafe_allow_html=True)
