import streamlit as st
import pandas as pd
import io
import time

# --- IMPORT LOCAL MODULES ---
# Ensure these files are in the same folder
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

# --- 2. CSS STYLING (Blue Theme) ---
st.markdown("""
<style>
    /* Background */
    .stApp { background-color: #0e1117; }
    
    /* Typography */
    h1, h2, h3, h4 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; letter-spacing: 1px; }
    p, label, .stMarkdown, .stTextInput, .stTextArea { font-family: 'Roboto', sans-serif !important; }
    .stDataFrame { font-family: 'Consolas', monospace !important; }
    
    /* Input Box Styling - RESIZABLE */
    textarea {
        font-family: 'Consolas', monospace !important;
        resize: vertical !important;
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
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #3b8ed0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .guide-title {
        color: #fff;
        font-weight: bold;
        font-size: 13px;
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

# --- 3. INITIALIZE ENGINES (Cached) ---
if 'ingestor' not in st.session_state:
    st.session_state.ingestor = NeuralIngestor()
    st.session_state.intent_engine = CognitiveIntentEngine()
    st.session_state.action_suite = ExecutionActionSuite()

# --- 4. SESSION STATE VARIABLES ---
if 'df' not in st.session_state: st.session_state.df = None
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'undo_stack' not in st.session_state: st.session_state.undo_stack = []

# --- 5. CORE FUNCTIONS ---

def log_msg(sender, msg):
    timestamp = pd.Timestamp.now().strftime("%H:%M")
    icon = "🦇" if sender == "JEFF" else "👤" if sender == "USER" else "⚠️"
    # Insert new message at the top
    entry = f"**{icon} [{timestamp}] {sender}:**\n\n{msg}\n\n---"
    st.session_state.chat_log.insert(0, entry)

def ingest_data():
    raw_text = st.session_state.get("raw_input_area", "")
    if not raw_text.strip():
        st.toast("Please paste data first.", icon="⚠️")
        return

    log_msg("JEFF", "Ingesting Data...")
    try:
        st.session_state.undo_stack = [] # Reset undo history
        
        # --- EXECUTE PIPELINE ---
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

    # Snapshot for Undo
    st.session_state.undo_stack.append(st.session_state.df.copy())

    try:
        # Web logic: Default to 'keep first' for dedupe to avoid blocking UI
        if intent["action"] == "dedupe" and "subset" not in intent["parameters"]:
             intent["parameters"]["keep"] = "first"

        new_df, result_msg = st.session_state.action_suite.execute(intent, st.session_state.df)
        st.session_state.df = new_df
        log_msg("JEFF", result_msg)
        
        # Clear input (Using session state assignment for reset)
        st.session_state["cmd_input_box"] = "" 
        
    except Exception as e:
        st.session_state.undo_stack.pop()
        log_msg("ERROR", str(e))
        st.error(f"Execution Error: {e}")

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


# --- 7. MAIN LAYOUT (4 COLUMNS) ---
st.title("🦇 JEFF DATA ANALYST")

# Define columns: Input(1) | Actions(1) | Guide(1) | Output(2.5)
col1, col2, col3, col4 = st.columns([1, 1, 1, 2.5], gap="small")

# === COLUMN 1: INPUT ===
with col1:
    st.subheader("1. INPUT")
    st.text_area("Raw Data:", height=250, key="raw_input_area", placeholder="Paste Excel/CSV content here...", label_visibility="collapsed")
    st.button("⚡ INGEST", on_click=ingest_data)

# === COLUMN 2: ACTIONS & SAVE ===
with col2:
    st.subheader("2. ACTION")
    # Command Input
    st.text_input("Command:", key="cmd_input_box", placeholder="Type here...", label_visibility="collapsed", on_change=run_command)
    
    # Execution Buttons
    st.button("▶ EXECUTE", on_click=run_command)
    st.button("⏪ UNDO LAST", on_click=undo_action)
    
    st.divider()
    
    # --- ROBUST SAVE LOGIC ---
    # Only show if data exists. No toggle button needed.
    if st.session_state.df is not None:
        st.markdown("**💾 Save File**")
        fname = st.text_input("Filename:", value="analysis", label_visibility="collapsed")
        
        # Prepare the file in memory
        clean_df = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            clean_df.to_excel(writer, index=False)
            
        # The Download Button acts as the "Save" action
        st.download_button(
            label="⬇️ DOWNLOAD EXCEL",
            data=buffer,
            file_name=f"{fname}.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        # Disabled state
        st.button("💾 SAVE FILE", disabled=True)

# === COLUMN 3: NEURAL GUIDE (HTML CARDS) ===
with col3:
    st.subheader("3. GUIDE")
    
    st.markdown("""
    <div style="height: 400px; overflow-y: auto; padding-right: 5px;">
        
        <div class="guide-card">
            <div class="guide-title">🛠️ EDITING</div>
            <div class="guide-cmd">Update Salary to 5000 where ID is 1</div>
            <div class="guide-cmd">Update Row 5 Name to Batman</div>
        </div>

        <div class="guide-card">
            <div class="guide-title">🧹 CLEANING</div>
            <div class="guide-cmd">Fill missing in Age with 0</div>
            <div class="guide-cmd">Replace 'NY' with 'New York'</div>
            <div class="guide-cmd">Dedupe</div>
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

# === COLUMN 4: OUTPUT (FILTERED) ===
with col4:
    if st.session_state.df is not None:
        # Filter out internal columns starting with '_'
        clean_view = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        rows, cols = clean_view.shape
        st.success(f"**ACTIVE DATA:** {rows} Rows | {cols} Columns")
        st.dataframe(clean_view, height=750, use_container_width=True)
    else:
        st.warning("WAITING FOR DATA...")
        st.markdown("<br><br><center><h3 style='color:#555;'>NO DATA LOADED</h3></center>", unsafe_allow_html=True)
