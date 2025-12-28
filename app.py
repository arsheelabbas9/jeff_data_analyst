import streamlit as st
import pandas as pd
import io
import time

# --- IMPORT YOUR LOCAL MODULES ---
# (Ensure these files are in the same folder as app.py)
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

# --- 2. CSS STYLING (THEME & LAYOUT) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #0e1117; }
    
    /* Fonts: Headers (Impact), UI (Roboto), Data (Consolas) */
    h1, h2, h3 { font-family: 'Impact', sans-serif !important; color: #3b8ed0 !important; letter-spacing: 1px; }
    .stTextInput, .stTextArea, .stButton { font-family: 'Roboto', sans-serif !important; }
    .stDataFrame, .stCode { font-family: 'Consolas', monospace !important; }
    
    /* Optimize Spacing */
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; max-width: 95%; }
    
    /* Button Styling */
    div.stButton > button {
        width: 100%;
        border-radius: 4px;
        font-weight: bold;
        text-transform: uppercase;
        border: 1px solid #3b8ed0;
    }
    div.stButton > button:hover {
        border-color: white;
        color: #3b8ed0;
    }
    
    /* Custom Box Borders */
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. INITIALIZE ENGINES (Cached for Speed) ---
if 'engines_loaded' not in st.session_state:
    st.session_state.ingestor = NeuralIngestor()
    st.session_state.intent_engine = CognitiveIntentEngine()
    st.session_state.action_suite = ExecutionActionSuite()
    st.session_state.engines_loaded = True

# --- 4. SESSION STATE VARIABLES ---
if 'df' not in st.session_state: st.session_state.df = None
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'undo_stack' not in st.session_state: st.session_state.undo_stack = []

# --- 5. CORE FUNCTIONS ---

def log_msg(sender, msg, type="info"):
    """Adds a message to the session log."""
    timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
    color = "#3b8ed0" if sender == "JEFF" else "#2ecc71" if sender == "USER" else "#e74c3c"
    icon = "🦇" if sender == "JEFF" else "👤" if sender == "USER" else "⚠️"
    
    # HTML formatted log entry
    entry = f"""
    <div style='margin-bottom: 5px; font-family: Consolas, monospace; font-size: 13px; border-bottom: 1px solid #222; padding-bottom: 4px;'>
        <span style='color: #666;'>[{timestamp}]</span> 
        <span style='color: {color}; font-weight: bold;'>{icon} {sender}:</span> 
        <span style='color: #ddd;'>{msg}</span>
    </div>
    """
    # Insert at top so users don't have to scroll down
    st.session_state.chat_log.insert(0, entry)

def undo_action():
    """Reverts to the previous DataFrame state."""
    if st.session_state.undo_stack:
        st.session_state.df = st.session_state.undo_stack.pop()
        log_msg("JEFF", "Time travel successful. Reverted to previous state.")
    else:
        st.toast("Nothing to undo!", icon="🚫")

def ingest_data():
    """Reads raw text from the input box and materializes it."""
    raw_text = st.session_state.raw_input_area
    if not raw_text.strip():
        st.toast("Please paste some data first.", icon="⚠️")
        return

    log_msg("JEFF", "Neural Ingest Initiated...")
    
    try:
        # Reset undo stack on new load
        st.session_state.undo_stack = []
        
        # Phase 2-6 Pipeline
        df = st.session_state.ingestor.build_diagnostic_dataframe(raw_text)
        schema = SchemaInferenceEngine().infer(df)
        df = DataMaterializer().materialize(df, schema)
        df = SchemaLockMaster().lock(df, schema)
        
        st.session_state.df = df
        log_msg("JEFF", f"Data Materialized. Shape: {df.shape}")
        st.toast("Data Loaded Successfully", icon="✅")
        
    except Exception as e:
        log_msg("ERROR", str(e))
        st.error(f"Ingest Failed: {e}")

def run_command():
    """Parses and executes the NLP command."""
    cmd = st.session_state.cmd_input_box
    if not cmd.strip(): return
    
    if st.session_state.df is None:
        st.toast("No data loaded.", icon="⚠️")
        return

    log_msg("USER", cmd)

    # Analyze Intent
    intent = st.session_state.intent_engine.analyze_command(cmd, st.session_state.df.columns)

    if intent["action"] == "unknown":
        suggestion = intent['suggestions'][0] if intent['suggestions'] else "Try 'Sort by [Col]'"
        log_msg("JEFF", f"Unknown command. {suggestion}", type="error")
        return

    # Save state for Undo
    st.session_state.undo_stack.append(st.session_state.df.copy())

    try:
        # Web-specific logic for interactive features
        if intent["action"] == "dedupe" and "subset" not in intent["parameters"]:
             # Default to 'first' on web to avoid complex modal logic
             intent["parameters"]["keep"] = "first"

        # Execute
        new_df, result_msg = st.session_state.action_suite.execute(intent, st.session_state.df)
        st.session_state.df = new_df
        log_msg("JEFF", result_msg)
        
        # Clear input box (requires key hack or just leave it)
        st.session_state.cmd_input_box = "" 
        
    except Exception as e:
        st.session_state.undo_stack.pop() # Revert save if failed
        log_msg("ERROR", str(e))

# --- 6. MAIN DASHBOARD LAYOUT ---

st.title("🦇 JEFF DATA ANALYST")

# Split: Left (35%) | Right (65%)
col_left, col_right = st.columns([1.2, 2.2], gap="large")

# === LEFT PANEL: CONTROL DECK ===
with col_left:
    st.subheader("1. SOURCE DATA")
    st.text_area(
        "Paste Excel/CSV data here:", 
        height=120, 
        key="raw_input_area",
        placeholder="Paste your raw data here...",
        label_visibility="collapsed"
    )
    st.button("⚡ INGEST DATA", on_click=ingest_data, type="primary")

    st.divider()

    st.subheader("2. NEURAL COMMAND")
    # Using a form allows hitting 'Enter' to submit
    with st.form(key='cmd_form', clear_on_submit=True):
        st.text_input(
            "Command:", 
            key="cmd_input_box", 
            placeholder="e.g., 'Sort by Salary' or 'Filter Age > 25'",
            label_visibility="collapsed"
        )
        c1, c2 = st.columns([3, 1])
        with c1:
            submit = st.form_submit_button("▶ EXECUTE COMMAND")
        with c2:
            # Undo is outside form usually, but Streamlit forms are tricky. 
            # We'll rely on the callback for the submit button.
            pass
            
    if submit:
        run_command()

    # Action Row
    b1, b2 = st.columns(2)
    with b1:
        st.button("⏪ UNDO LAST", on_click=undo_action)
    with b2:
        if st.session_state.df is not None:
            # Excel Export Logic
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                st.session_state.df.to_excel(writer, index=False)
            st.download_button(
                label="💾 DOWNLOAD",
                data=buffer,
                file_name="jeff_analysis.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.button("💾 DOWNLOAD", disabled=True)

    # Cheat Sheet (Always Visible Expander)
    with st.expander("📝 NEURAL GUIDE (CHEAT SHEET)", expanded=True):
        st.markdown("""
        <div style='font-family: Consolas; font-size: 12px; color: #aaa;'>
        <b>EDIT:</b> "Update Salary to 5000 where ID is 1"<br>
        <b>CLEAN:</b> "Fill missing in Age with 0"<br>
        <b>GROUP:</b> "Group by City sum Sales"<br>
        <b>STATS:</b> "Analyze Salary"<br>
        <b>SORT:</b> "Sort by Date Desc"<br>
        <b>PLOT:</b> "Plot Age"<br>
        <b>RENAME:</b> "Rename 'Old' to 'New'"
        </div>
        """, unsafe_allow_html=True)

    # Session Log (Fixed Height Scrollable)
    st.subheader("SESSION LOG")
    with st.container(height=250):
        # Render the HTML logs
        for log_entry in st.session_state.chat_log:
            st.markdown(log_entry, unsafe_allow_html=True)

# === RIGHT PANEL: DATA MONITOR ===
with col_right:
    if st.session_state.df is not None:
        # Status Bar
        rows, cols = st.session_state.df.shape
        st.markdown(f"""
        <div style='background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 5px solid #2ecc71; margin-bottom: 10px;'>
            <span style='color: white; font-weight: bold;'>SYSTEM STATUS:</span> <span style='color: #2ecc71;'>ONLINE</span> 
            &nbsp; | &nbsp; 
            <span style='color: white; font-weight: bold;'>ROWS:</span> <span style='color: #ccc;'>{rows}</span>
            &nbsp; | &nbsp; 
            <span style='color: white; font-weight: bold;'>COLS:</span> <span style='color: #ccc;'>{cols}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Main Data View
        st.dataframe(
            st.session_state.df, 
            use_container_width=True, 
            height=780,
            hide_index=True
        )
    else:
        # Empty State Placeholder
        st.info("AWAITING DATA INPUT...")
        st.code("""
        
        
            [ NO DATA LOADED ]
            
            1. Copy data from Excel/CSV
            2. Paste into the 'SOURCE DATA' box on the left
            3. Click 'INGEST DATA'
            
        
        """)
