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

# --- 2. CSS STYLING (COMPACT COMMAND CENTER) ---
st.markdown("""
<style>
    /* 1. Remove Top White Space (Crucial for Single View) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        max-width: 98% !important;
    }
    header { visibility: hidden; }
    footer { visibility: hidden; }

    /* 2. Global Dark Theme */
    .stApp { background-color: #0e1117; }
    
    /* 3. Typography */
    h1 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; font-size: 28px !important; margin-bottom: 0px !important; }
    h3 { font-family: 'Roboto', sans-serif !important; font-size: 16px !important; color: #888 !important; text-transform: uppercase; margin-top: 0px !important; }
    p, label, .stMarkdown, .stTextInput { font-family: 'Roboto', sans-serif !important; font-size: 13px !important; }
    .stDataFrame { font-family: 'Consolas', monospace !important; font-size: 12px !important; }

    /* 4. Inputs & Buttons (Compact) */
    textarea {
        font-family: 'Consolas', monospace !important;
        resize: none !important; /* Fixed size to prevent layout breaking */
        font-size: 11px !important;
        border: 1px solid #333 !important;
        background-color: #161920 !important;
    }
    .stTextInput input {
        background-color: #161920 !important;
        border: 1px solid #333 !important;
        color: #eee !important;
    }

    /* 5. BLUE BUTTONS (Standardized) */
    div.stButton > button {
        width: 100%;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px !important;
        background-color: #0e1117;
        color: #3b8ed0;
        border: 1px solid #3b8ed0;
        height: 32px !important;
        padding: 0px 10px !important;
    }
    div.stButton > button:hover {
        background-color: #3b8ed0;
        color: white;
    }
    div.stButton > button:active {
        background-color: #2a6fa8;
        color: white;
    }

    /* 6. TABS Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #0e1117;
    }
    .stTabs [data-baseweb="tab"] {
        height: 30px;
        padding: 0px 10px;
        font-size: 12px;
        color: #888;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #3b8ed0;
        border-bottom-color: #3b8ed0;
    }
    
    /* 7. Code Blocks in Guide */
    code {
        color: #a6e22e !important;
        background-color: #161920 !important;
        font-size: 10px !important;
        padding: 2px 4px !important;
        border: 1px solid #222;
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
        st.toast("Loaded", icon="✅")
    except Exception as e:
        log_msg("ERROR", str(e))
        st.error(f"Error: {e}")

def run_command():
    cmd = st.session_state.get("cmd_input_box", "")
    if not cmd.strip(): return
    if st.session_state.df is None:
        st.toast("No data loaded.", icon="⚠️")
        return
    log_msg("USER", cmd)
    intent = st.session_state.intent_engine.analyze_command(cmd, st.session_state.df.columns)
    
    if intent["action"] == "unknown":
        log_msg("JEFF", "Unknown command.")
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
        log_msg("JEFF", "Undo successful.")
        st.toast("Undone", icon="⏪")

# --- 6. SIDEBAR LOG ---
with st.sidebar:
    st.subheader("📜 SESSION LOG")
    st.divider()
    for log_entry in st.session_state.chat_log:
        st.markdown(log_entry)

# --- 7. MAIN LAYOUT (GRID SYSTEM) ---
st.title("🦇 JEFF DATA ANALYST")

# 4 Columns: Input (15%) | Actions (15%) | Guide (20%) | Output (50%)
# This ensures everything fits horizontally without scrolling.
c1, c2, c3, c4 = st.columns([0.8, 0.8, 1.2, 3], gap="small")

# === COL 1: INPUT ===
with c1:
    st.markdown("### 1. INPUT")
    # Fixed height to match the rest of the layout (approx 600px total workspace)
    st.text_area("Data", height=500, key="raw_input_area", placeholder="Paste Data...", label_visibility="collapsed")
    st.button("⚡ LOAD", on_click=ingest_data)

# === COL 2: CONTROLS ===
with c2:
    st.markdown("### 2. CONTROL")
    st.text_input("Cmd", key="cmd_input_box", placeholder="Command...", label_visibility="collapsed", on_change=run_command)
    
    st.button("▶ RUN", on_click=run_command)
    st.button("⏪ UNDO", on_click=undo_action)
    
    st.divider()
    
    # Save Logic
    if st.session_state.df is not None:
        fname = st.text_input("Name:", value="data", label_visibility="collapsed")
        clean_df = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            clean_df.to_excel(writer, index=False)
        st.download_button("⬇️ SAVE", data=buffer, file_name=f"{fname}.xlsx", mime="application/vnd.ms-excel")
    else:
        st.button("⬇️ SAVE", disabled=True)

# === COL 3: COMPACT TABS GUIDE ===
with c3:
    st.markdown("### 3. GUIDE")
    
    # TABS: The secret to "No Scroll" information density
    tab_edit, tab_clean, tab_ana = st.tabs(["EDIT", "CLEAN", "ANALYSIS"])
    
    with tab_edit:
        st.caption("**Modification**")
        st.markdown("`Update Salary to 5000 where ID is 1`")
        st.markdown("`Update Row 5 Name to Batman`")
        st.caption("**Structure**")
        st.markdown("`Rename 'Old' to 'New'`")
        st.markdown("`Delete Row 5`")
        
    with tab_clean:
        st.caption("**Fixing Data**")
        st.markdown("`Fill missing in Age with 0`")
        st.markdown("`Replace 'NY' with 'New York'`")
        st.markdown("`Dedupe` (Remove duplicates)")
        st.markdown("`Dedupe by Email`")

    with tab_ana:
        st.caption("**Insights**")
        st.markdown("`Group by City sum Sales`")
        st.markdown("`Analyze Salary`")
        st.caption("**Filters**")
        st.markdown("`Filter Age > 25`")
        st.markdown("`Sort by Date Desc`")

# === COL 4: OUTPUT (MAXIMIZED) ===
with c4:
    if st.session_state.df is not None:
        clean_view = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
        rows, cols = clean_view.shape
        # Header + Dataframe fits perfectly
        st.markdown(f"<h3 style='color:#2ecc71 !important; margin-bottom:5px;'>ACTIVE DATA: {rows} ROWS | {cols} COLS</h3>", unsafe_allow_html=True)
        st.dataframe(clean_view, height=580, use_container_width=True)
    else:
        # Placeholder to keep layout rigid
        st.markdown("### MONITOR")
        st.info("WAITING FOR DATA...")
        st.markdown("<br><br><br><br><center><h4 style='color:#444;'>NO SIGNAL</h4></center>", unsafe_allow_html=True)
