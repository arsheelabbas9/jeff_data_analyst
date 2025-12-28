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

# --- 2. AESTHETIC CSS (THE "GLASS" THEME) ---
st.markdown("""
<style>
    /* 1. Main Background - Deep Space Dark */
    .stApp {
        background-color: #0E1117;
    }

    /* 2. Hide Streamlit Bloat */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 3. Container Styling (The "Glass" Cards) */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161920;
        border: 1px solid #30333d;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    /* 4. Typography & Headers */
    h1 {
        font-family: 'Impact', sans-serif !important;
        color: #3b8ed0 !important;
        font-size: 32px !important;
        text-shadow: 0 0 10px rgba(59, 142, 208, 0.4);
        margin-bottom: 0px !important;
    }
    h3 {
        font-family: 'Roboto', sans-serif !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #888 !important;
        text-transform: uppercase;
        margin-top: 0px !important;
        letter-spacing: 1px;
    }
    
    /* 5. Blue Buttons (Cyber Style) */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
        background-color: #1f232d;
        color: #3b8ed0;
        border: 1px solid #3b8ed0;
        transition: all 0.2s ease-in-out;
        height: 38px;
    }
    div.stButton > button:hover {
        background-color: #3b8ed0;
        color: white;
        box-shadow: 0 0 12px rgba(59, 142, 208, 0.6);
        border-color: #3b8ed0;
    }
    div.stButton > button:active {
        background-color: #1a5c8e;
        color: white;
    }

    /* 6. Inputs (Clean & Dark) */
    .stTextInput input, .stTextArea textarea {
        background-color: #0e1117 !important;
        color: #e0e0e0 !important;
        border: 1px solid #333 !important;
        font-family: 'Consolas', monospace !important;
        border-radius: 5px;
    }
    .stTextArea textarea {
        resize: none; /* Lock size for perfect layout */
    }
    
    /* 7. Neural Guide Styling */
    .guide-item {
        background-color: #0e1117;
        border-left: 3px solid #3b8ed0;
        padding: 8px 10px;
        margin-bottom: 6px;
        border-radius: 0 4px 4px 0;
    }
    .guide-cmd {
        font-family: 'Consolas', monospace;
        font-size: 11px;
        color: #a6e22e; /* Code Green */
    }
    .guide-desc {
        font-family: 'Roboto', sans-serif;
        font-size: 11px;
        color: #888;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 2px;
    }

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

# --- 5. LOGIC FUNCTIONS ---
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
        st.toast("Loaded Successfully", icon="✅")
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

# --- 7. MAIN LAYOUT (SINGLE SCREEN GRID) ---
st.title("🦇 JEFF DATA ANALYST")

# 4 Columns: Input | Controls | Guide | Data
# Using 'border=True' creates the cards, which our CSS then beautifies.
c1, c2, c3, c4 = st.columns([1, 1, 1.2, 3], gap="small")

# === CARD 1: INPUT ===
with c1:
    with st.container(border=True):
        st.markdown("### 1. INPUT")
        st.text_area("Data", height=500, key="raw_input_area", placeholder="Paste Excel/CSV...", label_visibility="collapsed")
        st.button("⚡ LOAD DATA", on_click=ingest_data)

# === CARD 2: CONTROLS ===
with c2:
    with st.container(border=True):
        st.markdown("### 2. CONTROL")
        st.text_input("Cmd", key="cmd_input_box", placeholder="Type Command...", label_visibility="collapsed", on_change=run_command)
        
        st.button("▶ EXECUTE", on_click=run_command)
        st.button("⏪ UNDO", on_click=undo_action)
        
        st.markdown("---")
        
        # Save Logic (Always visible if data exists)
        if st.session_state.df is not None:
            fname = st.text_input("Filename:", value="data", label_visibility="collapsed")
            clean_df = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                clean_df.to_excel(writer, index=False)
            st.download_button("⬇️ DOWNLOAD", data=buffer, file_name=f"{fname}.xlsx", mime="application/vnd.ms-excel")
        else:
            st.button("⬇️ DOWNLOAD", disabled=True)

# === CARD 3: AESTHETIC GUIDE ===
with c3:
    with st.container(border=True):
        st.markdown("### 3. GUIDE")
        
        # Scrollable container for the guide
        with st.container(height=540, border=False):
            st.markdown("""
            
            <div class="guide-item">
                <div class="guide-desc">EDITING</div>
                <div class="guide-cmd">Update Salary to 5000 where ID is 1</div>
            </div>
            <div class="guide-item">
                <div class="guide-desc">EDITING</div>
                <div class="guide-cmd">Update Row 5 Name to Batman</div>
            </div>

            <div class="guide-item">
                <div class="guide-desc">CLEANING</div>
                <div class="guide-cmd">Fill missing in Age with 0</div>
            </div>
            <div class="guide-item">
                <div class="guide-desc">CLEANING</div>
                <div class="guide-cmd">Replace 'NY' with 'New York'</div>
            </div>
            <div class="guide-item">
                <div class="guide-desc">CLEANING</div>
                <div class="guide-cmd">Dedupe (Removes duplicates)</div>
            </div>

            <div class="guide-item">
                <div class="guide-desc">STRUCTURE</div>
                <div class="guide-cmd">Rename 'Old' to 'New'</div>
            </div>
            <div class="guide-item">
                <div class="guide-desc">STRUCTURE</div>
                <div class="guide-cmd">Delete Row 5</div>
            </div>
            
            <div class="guide-item">
                <div class="guide-desc">ANALYSIS</div>
                <div class="guide-cmd">Group by City sum Sales</div>
            </div>
            <div class="guide-item">
                <div class="guide-desc">ANALYSIS</div>
                <div class="guide-cmd">Analyze Salary</div>
            </div>
            <div class="guide-item">
                <div class="guide-desc">VISUALS</div>
                <div class="guide-cmd">Plot Age</div>
            </div>

            """, unsafe_allow_html=True)

# === CARD 4: MONITOR ===
with c4:
    with st.container(border=True):
        if st.session_state.df is not None:
            clean_view = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
            rows, cols = clean_view.shape
            st.markdown(f"<h3 style='color:#3b8ed0 !important; margin-bottom: 10px;'>ACTIVE DATA: {rows} ROWS | {cols} COLS</h3>", unsafe_allow_html=True)
            st.dataframe(clean_view, height=580, use_container_width=True)
        else:
            st.markdown("### MONITOR")
            st.info("WAITING FOR SIGNAL...")
            st.markdown("<br><br><br><center><h4 style='color:#333;'>NO DATA LOADED</h4></center><br><br><br>", unsafe_allow_html=True)
