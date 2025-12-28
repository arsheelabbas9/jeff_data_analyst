import streamlit as st
import pandas as pd
import io
import os
import pickle

# Import your existing engines (Keep these files in the same folder!)
from phase2_ingest import NeuralIngestor
from phase3_intent import CognitiveIntentEngine
from phase8_actions import ExecutionActionSuite
from phase5_schema import SchemaInferenceEngine
from phase6_materializer import DataMaterializer
from phase9_finalize import SchemaLockMaster

# --- CONFIGURATION ---
st.set_page_config(page_title="Jeff Data Analyst", page_icon="🦇", layout="wide")

# --- CSS STYLING (Dark Theme & Fonts) ---
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1 { font-family: 'Impact', sans-serif; color: #3b8ed0; }
    .stTextInput > div > div > input { font-family: 'Consolas', monospace; }
    .stTextArea > div > div > textarea { font-family: 'Consolas', monospace; }
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
    st.session_state.chat_log.append(entry)

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
        st.session_state.undo_stack = [] # Reset undo
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

    # Snapshot for Undo
    st.session_state.undo_stack.append(st.session_state.df.copy())

    try:
        # Interactive Logic for Web (Simplified)
        if intent["action"] == "dedupe" and "subset" not in intent["parameters"]:
             intent["parameters"]["keep"] = "first" # Default for web to avoid popup blocking

        df, msg_res = st.session_state.action_suite.execute(intent, st.session_state.df)
        st.session_state.df = df
        log_msg("JEFF", msg_res)
        
        # Clear input after run
        st.session_state.cmd_input = "" 
        
    except Exception as e:
        st.session_state.undo_stack.pop()
        log_msg("ERROR", str(e))

# --- LAYOUT ---
st.title("🦇 JEFF DATA ANALYST")

col1, col2 = st.columns([1, 2])

# LEFT PANEL (Controls)
with col1:
    st.subheader("1. Source Data")
    st.text_area("Paste Data Here:", height=150, key="raw_input")
    st.button("⚡ INGEST DATA", on_click=process_data, use_container_width=True)
    
    st.divider()
    
    st.subheader("2. Command Center")
    st.text_input("Neural Command Line:", placeholder="Type command (e.g. 'Sort Salary')...", key="cmd_input", on_change=execute_command)
    
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1: st.button("▶ EXECUTE", on_click=execute_command, use_container_width=True)
    with b_col2: st.button("⏪ UNDO", on_click=undo, use_container_width=True)
    with b_col3: 
        if st.session_state.df is not None:
            # Web Export Logic
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                st.session_state.df.to_excel(writer, index=False)
                writer.close() # Important to close before getting value
                
            st.download_button(
                label="💾 SAVE",
                data=buffer,
                file_name="jeff_analysis.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )
        else:
            st.button("💾 SAVE", disabled=True, use_container_width=True)

    with st.expander("📝 COMMAND CHEAT SHEET", expanded=True):
        st.markdown("""
        **EDIT:** `Update Salary to 5000 where ID is 1`  
        **CLEAN:** `Fill missing in Age with 0`  
        **GROUP:** `Group by City sum Sales`  
        **STATS:** `Analyze Salary`  
        **PLOT:** `Plot Age`  
        """)

    st.subheader("Session Log")
    chat_container = st.container(height=200)
    for chat in st.session_state.chat_log:
        chat_container.markdown(chat)

# RIGHT PANEL (Data View)
with col2:
    if st.session_state.df is not None:
        st.success(f"SYSTEM STATUS: ACTIVE | ROWS: {len(st.session_state.df)} | COLS: {len(st.session_state.df.columns)}")
        st.dataframe(st.session_state.df, use_container_width=True, height=600)
    else:
        st.info("SYSTEM STATUS: WAITING FOR DATA...")
        st.code("\n\n   [ NO DATA LOADED ]\n   PASTE DATA IN LEFT PANEL\n\n")