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

# --- 2. PREMIUM AESTHETIC CSS ---
st.markdown("""
<style>
    /* 1. Background & Reset */
    .stApp { background-color: #0E1117; }
    #MainMenu, footer, header { visibility: hidden; }
    
    /* 2. Glass Cards (Uniform Height & Look) */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161920;
        border: 1px solid #30333d;
        border-radius: 12px; /* Softer corners */
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    /* 3. Typography (Clean & Modern) */
    h1 { 
        font-family: 'Impact', sans-serif !important; 
        color: #3b8ed0 !important; 
        font-size: 36px !important; 
        margin: 0 0 10px 0 !important; 
        text-shadow: 0 0 15px rgba(59, 142, 208, 0.3);
    }
    h3 { 
        font-family: 'Roboto', sans-serif !important; 
        font-size: 14px !important; 
        font-weight: 800 !important; 
        color: #888 !important; 
        text-transform: uppercase; 
        letter-spacing: 2px;
        margin-bottom: 15px !important;
    }
    
    /* 4. MASSIVE INPUT BOX */
    .stTextArea textarea {
        background-color: #0e1117 !important;
        color: #e0e0e0 !important;
        border: 1px solid #333 !important;
        font-family: 'Consolas', monospace !important;
        border-radius: 8px;
        min-height: 700px !important; /* Huge height */
        font-size: 11px !important;
        resize: none;
    }

    /* 5. Cyber Blue Buttons */
    div.stButton > button {
        width: 100%; border-radius: 8px; font-weight: 700; font-size: 12px; text-transform: uppercase;
        background-color: #1f232d; color: #3b8ed0; border: 1px solid #3b8ed0;
        transition: all 0.2s; height: 42px; letter-spacing: 1px;
    }
    div.stButton > button:hover { 
        background-color: #3b8ed0; color: white; 
        box-shadow: 0 0 15px rgba(59, 142, 208, 0.5); 
        transform: translateY(-1px);
    }
    
    /* 6. Guide Details Styling */
    .cmd-box {
        margin-bottom: 12px;
        border-bottom: 1px solid #222;
        padding-bottom: 8px;
    }
    .cmd-title {
        color: #fff; font-weight: bold; font-size: 12px; margin-bottom: 4px; display: block;
    }
    .cmd-desc {
        color: #666; font-size: 10px; font-style: italic; margin-bottom: 6px; display: block;
    }
    .cmd-code {
        font-family: 'Consolas', monospace; color: #a6e22e; background: #0e1117;
        padding: 4px 8px; border-radius: 4px; border: 1px solid #333; font-size: 11px;
    }

    /* 7. Tabs Customization */
    .stTabs [data-baseweb="tab-list"] { background-color: #161920; gap: 5px; }
    .stTabs [data-baseweb="tab"] { height: 35px; background-color: #0e1117; border-radius: 6px 6px 0 0; color: #666; font-size: 11px; font-weight: bold; border: 1px solid #222; border-bottom: none; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #3b8ed0; background-color: #1c1f26; border-top: 2px solid #3b8ed0; }
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
    st.subheader("SESSION LOG")
    st.divider()
    for log_entry in st.session_state.chat_log:
        st.markdown(log_entry)

# --- 7. MAIN LAYOUT ---
st.title("🦇 JEFF DATA ANALYST")

c1, c2, c3, c4 = st.columns([1, 1, 1.3, 3], gap="small")

# === CARD 1: INPUT ===
with c1:
    with st.container(border=True):
        st.markdown("### INPUT")
        # CSS forces min-height: 700px
        st.text_area("Data", height=700, key="raw_input_area", placeholder="Paste Excel/CSV...", label_visibility="collapsed")
        st.button("⚡ LOAD DATA", on_click=ingest_data)

# === CARD 2: CONTROLS ===
with c2:
    with st.container(border=True):
        st.markdown("### CONTROL")
        st.text_input("Cmd", key="cmd_input_box", placeholder="Type Command...", label_visibility="collapsed", on_change=run_command)
        
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

# === CARD 3: DETAILED NEURAL GUIDE ===
with c3:
    with st.container(border=True):
        st.markdown("### GUIDE")
        
        # TABBED INTERFACE for Organization
        t1, t2, t3, t4 = st.tabs(["EDIT", "CLEAN", "STRUCT", "DATA"])
        
        with t1: # Editing
            st.markdown("""
            <div class="cmd-box">
                <span class="cmd-title">Update Cell Value</span>
                <span class="cmd-desc">Change a specific value based on ID or criteria.</span>
                <div class="cmd-code">Update Salary to 5000 where ID is 1</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Update by Row Index</span>
                <span class="cmd-desc">Surgical edit using the row number (0, 1, 2...).</span>
                <div class="cmd-code">Update Row 5 Name to Batman</div>
            </div>
            """, unsafe_allow_html=True)

        with t2: # Cleaning
            st.markdown("""
            <div class="cmd-box">
                <span class="cmd-title">Fill Missing Data</span>
                <span class="cmd-desc">Replace empty/null cells with a safe default.</span>
                <div class="cmd-code">Fill missing in Age with 0</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Global Replace</span>
                <span class="cmd-desc">Find and replace text across the entire dataset.</span>
                <div class="cmd-code">Replace 'NY' with 'New York'</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Deduplication</span>
                <span class="cmd-desc">Remove identical rows to clean up data.</span>
                <div class="cmd-code">Dedupe</div>
            </div>
            """, unsafe_allow_html=True)

        with t3: # Structure
            st.markdown("""
            <div class="cmd-box">
                <span class="cmd-title">Rename Column</span>
                <span class="cmd-desc">Change headers to be more readable.</span>
                <div class="cmd-code">Rename 'Old_Name' to 'New_Name'</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Delete Row</span>
                <span class="cmd-desc">Remove a specific row by its index number.</span>
                <div class="cmd-code">Delete Row 5</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Delete Column</span>
                <span class="cmd-desc">Remove an entire column permanently.</span>
                <div class="cmd-code">Delete Column 'Tax'</div>
            </div>
            """, unsafe_allow_html=True)

        with t4: # Analysis
            st.markdown("""
            <div class="cmd-box">
                <span class="cmd-title">Pivot / Grouping</span>
                <span class="cmd-desc">Aggregate data to find totals or counts.</span>
                <div class="cmd-code">Group by City sum Sales</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Quick Statistics</span>
                <span class="cmd-desc">Get Mean, Median, Max, and Min instantly.</span>
                <div class="cmd-code">Analyze Salary</div>
            </div>
            <div class="cmd-box">
                <span class="cmd-title">Filtering</span>
                <span class="cmd-desc">Isolate specific data rows.</span>
                <div class="cmd-code">Filter Age > 25</div>
            </div>
             <div class="cmd-box">
                <span class="cmd-title">Sorting</span>
                <span class="cmd-desc">Order data Ascending or Descending.</span>
                <div class="cmd-code">Sort by Date Desc</div>
            </div>
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
