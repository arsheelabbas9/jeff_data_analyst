import streamlit as st
import pandas as pd
import io

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

# --- 2. HYPER-POLISHED CSS ---
st.markdown("""
<style>
    /* 1. GLOBAL RESET & THEME */
    .stApp { background-color: #0b0e11; }
    #MainMenu, footer, header { visibility: hidden; }
    
    /* 2. GLASS CONTAINERS */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #151921;
        border: 1px solid #2a2e35;
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }

    /* 3. TYPOGRAPHY */
    h1 { 
        font-family: 'Impact', sans-serif !important; 
        color: #3b8ed0 !important; 
        font-size: 34px !important; 
        text-shadow: 0 0 10px rgba(59, 142, 208, 0.4);
        margin-bottom: 5px !important;
    }
    h3 { 
        font-family: 'Roboto', sans-serif !important; 
        font-size: 13px !important; 
        font-weight: 900 !important; 
        color: #6c757d !important; 
        text-transform: uppercase; 
        letter-spacing: 1.5px;
        margin-bottom: 12px !important;
    }
    
    /* 4. DATA INPUT BOX (The Big One) */
    .data-input textarea {
        background-color: #080a0c !important;
        color: #a6e22e !important; /* Matrix Green */
        border: 1px solid #333 !important;
        font-family: 'Consolas', monospace !important;
        border-radius: 6px;
        min-height: 400px !important;
        font-size: 12px !important;
        resize: none;
    }
    
    /* 5. COMMAND INPUT BOX (The New Box) */
    .cmd-input textarea {
        background-color: #1c2128 !important;
        color: #ffffff !important; /* White Text */
        border: 1px solid #3b8ed0 !important; /* Blue Border */
        font-family: 'Consolas', monospace !important;
        border-radius: 6px;
        min-height: 100px !important; /* Shorter Box */
        font-size: 13px !important;
        resize: none;
    }

    /* 6. BUTTONS */
    div.stButton > button {
        width: 100%; border-radius: 6px; font-weight: 700; font-size: 12px;
        background-color: #1f232d; color: #3b8ed0; border: 1px solid #3b8ed0;
        transition: all 0.2s; height: 38px; text-transform: uppercase;
    }
    div.stButton > button:hover { 
        background-color: #3b8ed0; color: white; 
        box-shadow: 0 0 10px rgba(59, 142, 208, 0.5); 
    }

    /* 7. CUSTOM TABS */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent; gap: 8px; border-bottom: 1px solid #2a2e35; padding-bottom: 0px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 35px; background-color: transparent; color: #555; font-size: 11px; font-weight: 700; border: none; padding: 0 10px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #3b8ed0; background-color: transparent; border-bottom: 2px solid #3b8ed0;
    }

    /* 8. GUIDE CONTENT */
    .cmd-box { margin-bottom: 10px; border-left: 2px solid #333; padding-left: 10px; }
    .cmd-title { color: #ddd; font-weight: bold; font-size: 12px; display: block; }
    .cmd-desc { color: #666; font-size: 10px; font-style: italic; margin-bottom: 4px; display: block; }
    .cmd-code { 
        font-family: 'Consolas', monospace; color: #a6e22e; 
        background: #080a0c; padding: 2px 6px; border-radius: 4px; 
        border: 1px solid #222; font-size: 10px; 
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

# --- 5. LOGIC ---
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
        # Note: We don't auto-clear text_area easily without rerun, so we keep it or rely on user
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
    st.subheader("SESSION LOG")
    st.divider()
    for log_entry in st.session_state.chat_log:
        st.markdown(log_entry)

# --- 7. MAIN LAYOUT ---
st.title("🦇 JEFF DATA ANALYST")

# [CHANGE]: Symmetrical Layout [2.0, 1.2, 1.3, 2.0]
# Input (2.0) == Monitor (2.0)
c1, c2, c3, c4 = st.columns([2.0, 1.2, 1.3, 2.0], gap="small")

# === CARD 1: INPUT ===
with c1:
    with st.container(border=True):
        st.markdown("### INPUT")
        # Added specific class for styling
        st.markdown('<div class="data-input">', unsafe_allow_html=True)
        st.text_area("Data", height=400, key="raw_input_area", placeholder="Paste Excel/CSV...", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        st.button("⚡ LOAD DATA", on_click=ingest_data)

# === CARD 2: CONTROLS ===
with c2:
    with st.container(border=True):
        st.markdown("### CONTROL")
        
        # [CHANGE] Replaced text_input with text_area (The Box)
        st.markdown('<div class="cmd-input">', unsafe_allow_html=True)
        st.text_area("Cmd", height=100, key="cmd_input_box", placeholder="Type Command Here...", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.button("▶ EXECUTE", on_click=run_command)
        st.button("⏪ UNDO", on_click=undo_action)
        
        st.markdown("---")
        
        if st.session_state.df is not None:
            fname = st.text_input("Filename:", value="data", label_visibility="collapsed")
            clean_df = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                clean_df.to_excel(writer, index=False)
            st.download_button("⬇️ DOWNLOAD", data=buffer, file_name=f"{fname}.xlsx", mime="application/vnd.ms-excel")
        else:
            st.button("⬇️ DOWNLOAD", disabled=True)

# === CARD 3: GUIDE ===
with c3:
    with st.container(border=True):
        st.markdown("### GUIDE")
        
        t1, t2, t3, t4 = st.tabs(["EDIT", "CLEAN", "STRUCT", "DATA"])
        
        with t1:
            st.markdown("""
            <div class="cmd-box"><span class="cmd-title">Update Cell</span><span class="cmd-desc">Change specific value.</span><div class="cmd-code">Update Salary to 5000 where ID is 1</div></div>
            <div class="cmd-box"><span class="cmd-title">Update Row</span><span class="cmd-desc">Edit by row number.</span><div class="cmd-code">Update Row 5 Name to Batman</div></div>
            """, unsafe_allow_html=True)
        with t2:
            st.markdown("""
            <div class="cmd-box"><span class="cmd-title">Fill Missing</span><span class="cmd-desc">Fix empty cells.</span><div class="cmd-code">Fill missing in Age with 0</div></div>
            <div class="cmd-box"><span class="cmd-title">Replace</span><span class="cmd-desc">Global text replace.</span><div class="cmd-code">Replace 'NY' with 'New York'</div></div>
            <div class="cmd-box"><span class="cmd-title">Dedupe</span><span class="cmd-desc">Remove duplicates.</span><div class="cmd-code">Dedupe</div></div>
            """, unsafe_allow_html=True)
        with t3:
            st.markdown("""
            <div class="cmd-box"><span class="cmd-title">Rename</span><span class="cmd-desc">Change column headers.</span><div class="cmd-code">Rename 'Old' to 'New'</div></div>
            <div class="cmd-box"><span class="cmd-title">Delete Row</span><span class="cmd-desc">Remove row by index.</span><div class="cmd-code">Delete Row 5</div></div>
            """, unsafe_allow_html=True)
        with t4:
            st.markdown("""
            <div class="cmd-box"><span class="cmd-title">Pivot/Group</span><span class="cmd-desc">Aggregate data.</span><div class="cmd-code">Group by City sum Sales</div></div>
            <div class="cmd-box"><span class="cmd-title">Stats</span><span class="cmd-desc">Quick statistics.</span><div class="cmd-code">Analyze Salary</div></div>
            <div class="cmd-box"><span class="cmd-title">Sort/Filter</span><span class="cmd-desc">Organize view.</span><div class="cmd-code">Filter Age > 25</div></div>
            """, unsafe_allow_html=True)

# === CARD 4: MONITOR ===
with c4:
    with st.container(border=True):
        if st.session_state.df is not None:
            clean_view = st.session_state.df.loc[:, ~st.session_state.df.columns.str.startswith('_')]
            rows, cols = clean_view.shape
            st.markdown(f"<h3 style='color:#3b8ed0 !important; margin-bottom: 10px;'>ACTIVE DATA: {rows} ROWS | {cols} COLS</h3>", unsafe_allow_html=True)
            st.dataframe(clean_view, height=750, use_container_width=True)
        else:
            st.markdown("### MONITOR")
            st.info("WAITING FOR SIGNAL...")
            st.markdown("<br><br><br><br><center><h4 style='color:#333;'>NO DATA LOADED</h4></center><br><br><br>", unsafe_allow_html=True)
