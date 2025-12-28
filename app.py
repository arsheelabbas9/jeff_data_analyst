import streamlit as st
import pandas as pd
import io
import os
import pickle

# Import your existing engines
from phase2_ingest import NeuralIngestor
from phase3_intent import CognitiveIntentEngine
from phase8_actions import ExecutionActionSuite
from phase5_schema import SchemaInferenceEngine
from phase6_materializer import DataMaterializer
from phase9_finalize import SchemaLockMaster

# --- CONFIGURATION (Wide Mode for Single Screen Feel) ---
st.set_page_config(page_title="Jeff Data Analyst", page_icon="🦇", layout="wide")

# --- CSS STYLING (Force Dark Theme & Clean Fonts) ---
st.markdown("""
<style>
    /* Force main background color */
    .stApp { background-color: #0e1117; }
    
    /* Headers */
    h1, h2, h3 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea { font-family: 'Consolas', monospace !important; }
    
    /* Remove top padding to maximize screen space */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Button Styling */
    div.stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE ENGINES ---
if 'ingestor' not in st.session_state:
    st.session_state.ingestor = NeuralIngestor()
    st.session_state.intent_engine = CognitiveIntentEngine()
    st.session_state.action_suite = ExecutionActionSuite()

# --- STATE MANAGEMENT ---
if 'df' not in st.session_state: st.session_state.df = None
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'undo_stack' not in st.session_state: st.session_state.undo_stack = []

# --- FUNCTIONS ---
def log_msg(sender, msg):
    timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
    entry = f"**[{timestamp}] {sender}:** {msg}"
    # Prepend to list so newest is at top (better for dashboard view)
    st.session_state.chat_log.insert(0, entry)

def undo():
    if st.session_state.undo_stack:
        st.session_state.df = st.session_state.undo_stack.pop()
        log_msg("JEFF", "⏪ Undo Successful.")
    else:
        st.warning("Nothing to undo.")

def process_data():
    raw_text = st.session_state.raw_input
    if not raw_text: return
    
    log_msg("JEFF", "🧠 Ingesting Data...")
    try:
        st.session_state.undo_stack = [] 
        df = st.session_state.ingestor.build_diagnostic_dataframe(raw_text)
        schema = SchemaInferenceEngine().infer(df)
        df = DataMaterializer().materialize(df, schema)
        df = SchemaLockMaster().lock(df, schema)
        
        st.session_state.df = df
        log_msg("JEFF", f"✅ Data Materialized. {len(df)} rows.")
    except Exception as e:
        st.error(f"Error: {e}")

def execute_command():
    cmd = st.session_state.cmd_input
    if not cmd: return
    
    if st.session_state.df is None:
        st.error("Please load data first.")
        return

    log_msg("USER", cmd)
    intent = st.session_state.intent_engine.analyze_command(cmd, st.session_state.df.columns)

    if intent["action"] == "unknown":
        log_msg("JEFF", f"⚠️ Unknown command. {intent['suggestions'][0] if intent['suggestions'] else ''}")
        return

    st.session_state.undo_stack.append(st.session_state.df.copy())

    try:
        if intent["action"] == "dedupe" and "subset" not in intent["parameters"]:
             intent["parameters"]["keep"] = "first" 

        df, msg_res = st.session_state.action_suite.execute(intent, st.session_state.df)
        st.session_state.df = df
        log_msg("JEFF", msg_res)
        st.session_state.cmd_input = "" 
        
    except Exception as e:
        st.session_state.undo_stack.pop()
        log_msg("ERROR", str(e))

# --- MAIN DASHBOARD LAYOUT ---
st.title("🦇 JEFF DATA ANALYST")

# Create two main columns: Left (Controls) 35% | Right (Data) 65%
col1, col2 = st.columns([1.2, 2])

# ================= LEFT PANEL (CONTROLS) =================
with col1:
    # 1. INPUT
    st.markdown("### 1. Source Data")
    st.text_area("Paste Data:", height=100, key="raw_input", label_visibility="collapsed", placeholder="Paste Excel/CSV data here...")
    st.button("⚡ INGEST DATA", on_click=process_data, type="primary")
    
    st.divider()
    
    # 2. COMMANDS
    st.markdown("### 2. Command Center")
    st.text_input("Command:", key="cmd_input", on_change=execute_command, label_visibility="collapsed", placeholder="Type command (e.g. 'Sort Salary')...")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.button("▶ RUN", on_click=execute_command)
    with c2: st.button("⏪ UNDO", on_click=undo)
    with c3:
        if st.session_state.df is not None:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                st.session_state.df.to_excel(writer, index=False)
            st.download_button("💾 SAVE", data=buffer, file_name="jeff_analysis.xlsx", mime="application/vnd.ms-excel")
        else:
            st.button("💾 SAVE", disabled=True)

    # 3. CHEAT SHEET (Full Details)
    with st.expander("📝 NEURAL GUIDE (CHEAT SHEET)", expanded=False):
        st.markdown("""
        **EDITING**
        * `Update Salary to 5000 where ID is 1`
        * `Update Row 5 Name to Batman`
        
        **STRUCTURE**
        * `Rename 'Old' to 'New'`
        * `Dedupe` (Removes duplicates)
        * `Delete Row 5` | `Delete Column 'Tax'`
        
        **CLEANING**
        * `Fill missing in Age with 0`
        * `Replace 'NY' with 'New York'`
        
        **ANALYSIS**
        * `Group by City sum Sales`
        * `Analyze Salary` (Stats)
        * `Filter Age > 25`
        * `Sort by Date Desc`
        * `Plot Age`
        """)

    # 4. CHAT LOG (Scrollable Box)
    st.markdown("### Session Log")
    # This container makes the log scroll internally, so the page doesn't grow
    with st.container(height=300):
        for chat in st.session_state.chat_log:
            st.markdown(chat)

# ================= RIGHT PANEL (DATA VIEW) =================
with col2:
    if st.session_state.df is not None:
        # Status Bar
        st.success(f"**SYSTEM ONLINE** | ROWS: {len(st.session_state.df)} | COLS: {len(st.session_state.df.columns)}")
        # Dataframe takes up full remaining height (800px)
        st.dataframe(st.session_state.df, use_container_width=True, height=750)
    else:
        st.info("WAITING FOR DATA INPUT...")
        # Placeholder visual
        st.code("\n\n\n\t\t[ AWAITING SIGNAL ]\n\t\tPASTE DATA IN LEFT PANEL\n\n\n")
