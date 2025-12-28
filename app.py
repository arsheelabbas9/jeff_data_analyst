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

# --- 2. CSS STYLING (THEME & RESIZABLE INPUT) ---
st.markdown("""
<style>
    /* Background */
    .stApp { background-color: #0e1117; }
    
    /* Typography */
    h1, h2, h3, h4 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; letter-spacing: 1px; }
    p, label, .stMarkdown { font-family: 'Roboto', sans-serif !important; }
    .stDataFrame { font-family: 'Consolas', monospace !important; }
    
    /* Input Box Styling - FORCE RESIZABLE */
    textarea {
        font-family: 'Consolas', monospace !important;
        resize: vertical !important; /* Adds the drag handle */
        min-height: 150px !important;
    }
    
    /* Button Styling (Blue) */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        background-color: #0e1117;
        color: #3b8ed0;
        border: 1px solid #3b8ed0;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #3b8ed0;
        color: white;
        box-shadow: 0 0 10px rgba(59, 142, 208, 0.5);
    }
    div.stButton > button:active {
        background-color: #2a6fa8;
        color: white;
    }
    
    /* NEURAL GUIDE CARDS */
    .guide-card {
        background-color: #1c1f26;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        border-left: 4px solid #3b8ed0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .guide-title {
        color: #fff;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 5px;
    }
    .guide-cmd {
        background-color: #0e1117;
        color: #a6e22e; /* Code Green */
        padding: 4px 8px;
        border-radius: 4px;
        font-family: 'Consolas', monospace;
        font-size: 11px;
        display: block;
        margin-top: 4px;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. INITIALIZE ENGINES ---
if 'engines_loaded' not in st.session_state:
    st.session_state.ingestor = NeuralIngestor()
    st.session_state.intent_engine = CognitiveIntentEngine()
    st.session_state.action_suite = ExecutionActionSuite()
    st.session_state.engines_loaded = True

# --- 4. STATE ---
if 'df' not in st.session_state: st.session_state.df = None
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'undo_stack' not in st.session_state: st.session_state.undo_stack = []
if 'save_mode' not in st.session_state: st.session_state.save_mode = False

# --- 5. LOGIC ---

def log_msg(sender, msg):
    timestamp = pd.Timestamp.now().strftime("%H:%M")
    icon = "🦇" if sender == "JEFF" else "👤" if sender == "USER" else "⚠️"
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
        st.toast("Data Loaded", icon="✅")
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

def toggle_save():
    st.session_state.save_mode = not st.session_state.save_mode

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("📜 SESSION LOG")
    st.divider()
    for log_entry in st.session_state.chat_log:
        st.markdown(log_entry)

# --- 7. MAIN LAYOUT ---
st.title("🦇 JEFF DATA ANALYST")

col1, col2, col3, col4 = st.columns([1, 1, 1.2, 2.5], gap="small")

# === COL 1: INPUT (RESIZABLE) ===
with col1:
    st.subheader("1. INPUT")
    # Height set to 250px default, but CSS allows dragging it larger
    st.text_area("Raw Data:", height=250, key="raw_input_area", placeholder="Paste Excel/CSV...", label_visibility="collapsed")
    st.button("⚡ INGEST", on_click=ingest_data)

# === COL 2: ACTIONS ===
with col2:
    st.subheader("2. ACTION")
    st.text_input("Command:", key="cmd_input_box", placeholder="Type here...", label_visibility="collapsed", on_change=run_command)
    st.button("▶ EXECUTE", on_click=run_command)
    st.button("⏪ UNDO LAST", on_click=undo_action)
    
    if st.button("💾 SAVE FILE"):
        toggle_save()
        
    if st.session_state.save_mode and st.session_state.df is not None:
        fname = st.text_input("Filename:", value="analysis")
        if fname:
            final_name = f"{fname}.xlsx"
            buffer = io.BytesIO()
            clean_df = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                clean_df.to_excel(writer, index=False)
            st.download_button(label=f"⬇️ Download", data=buffer, file_name=final_name, mime="application/vnd.ms-excel")

# === COL 3: NEURAL GUIDE ===
with col3:
    st.subheader("3. GUIDE")
    
    st.markdown("""
    <div style="height: 450px; overflow-y: auto; padding-right: 5px;">
        
        <div class="guide-card">
            <div class="guide-title">🛠️ EDITING</div>
            <div class="guide-cmd">Update Salary to 5000 where ID is 1</div>
            <div class="guide-cmd">Update Row 5 Name to Batman</div>
        </div>

        <div class="guide-card">
            <div class="guide-title">🧹 CLEANING</div>
            <div class="guide-cmd">Fill missing in Age with 0</div>
            <div class="guide-cmd">Replace 'NY' with 'New York'</div>
            <div class="guide-cmd">Dedupe (Removes duplicates)</div>
        </div>

        <div class="guide-card">
            <div class="guide-title">🏷️ STRUCTURE</div>
            <div class="guide-cmd">Rename 'Old' to 'New'</div>
            <div class="guide-cmd">Delete Row 5</div>
            <div class="guide-cmd">Delete Column 'Tax'</div>
        </div>

        <div class="guide-card">
            <div class="guide-title">📊 ANALYSIS</div>
            <div class="guide-cmd">Group by City sum Sales</div>
            <div class="guide-cmd">Analyze Salary</div>
            <div class="guide-cmd">Filter Age > 25</div>
            <div class="guide-cmd">Sort by Date Desc</div>
        </div>

    </div>
    """, unsafe_allow_html=True)

# === COL 4: OUTPUT ===
with col4:
    if st.session_state.df is not None:
        clean_view = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        rows, cols = clean_view.shape
        st.success(f"**ACTIVE DATA:** {rows} Rows | {cols} Columns")
        st.dataframe(clean_view, height=750, use_container_width=True)
    else:
        st.warning("WAITING FOR DATA...")
        st.markdown("<br><br><center><h3>NO DATA</h3></center>", unsafe_allow_html=True)
