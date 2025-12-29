import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

class ExecutionActionSuite:
    def execute(self, intent, df):
        """
        Returns:
            df: Modified DataFrame
            msg: Status message
            artifact: Dictionary {'type': 'text'|'plot', 'content': ..., 'filename': ...} 
                      to be used for file downloads.
        """
        action = intent['action']
        params = intent['parameters']
        msg = "Action completed."
        artifact = None
        
        try:
            # --- 1. ADDING STRUCTURE (New Features) ---
            if action == 'add_col':
                col = params.get('column')
                if col and col not in df.columns:
                    df[col] = pd.NA # Initialize with empty values
                    msg = f"Added new column '{col}'."
                elif col in df.columns:
                    msg = f"Column '{col}' already exists."
                else:
                    msg = "No column name provided."

            elif action == 'add_row':
                # Append an empty row with the same index logic
                new_idx = len(df)
                df.loc[new_idx] = [pd.NA] * len(df.columns)
                msg = f"Added new empty row at index {new_idx}."

            # --- 2. EDITING (Fixed Update Logic) ---
            elif action == 'update':
                val = params.get('value')
                col = params.get('column')
                
                # Update by Row Index
                if 'row_index' in params and col:
                    idx = params['row_index']
                    if idx in df.index:
                        # Attempt type conversion
                        try:
                            # If column is numeric but val is string number
                            if pd.api.types.is_numeric_dtype(df[col]):
                                val = float(val)
                        except: pass 
                        
                        df.at[idx, col] = val
                        msg = f"Updated Row {idx}, Column '{col}' to '{val}'"
                    else:
                        msg = f"Row index {idx} not found."
                
                # Update by ID (e.g., Update Status where ID is 5)
                elif 'id_val' in params and col:
                    id_val = params['id_val']
                    # Smart search for ID column
                    id_col = next((c for c in df.columns if 'id' in c.lower()), None)
                    if id_col:
                        mask = df[id_col] == id_val
                        df.loc[mask, col] = val
                        msg = f"Updated '{col}' to '{val}' where {id_col} is {id_val}"
                    else:
                        msg = "No 'ID' column found to update by."

            # --- 3. DEDUPE (Fixed Logic) ---
            elif action == 'dedupe':
                col = params.get('column')
                before = len(df)
                if col:
                    # Dedupe based on specific subset
                    df = df.drop_duplicates(subset=[col])
                    msg = f"Removed duplicates based on column '{col}'. ({before - len(df)} removed)"
                else:
                    # Dedupe identical rows
                    df = df.drop_duplicates()
                    msg = f"Removed identical rows. ({before - len(df)} removed)"

            # --- 4. DATA OPS (Filter, Sort, Group) ---
            elif action == 'filter':
                col = params.get('column')
                op = params.get('operator')
                val = params.get('value')
                if col and op and val:
                    try: val = float(val)
                    except: pass
                    
                    if op == '>': df = df[df[col] > val]
                    elif op == '<': df = df[df[col] < val]
                    elif op == '==': df = df[df[col] == val]
                    msg = f"Filtered {col} {op} {val}. Remaining: {len(df)}"

            elif action == 'sort':
                col = params.get('column')
                asc = params.get('ascending', True)
                if col:
                    df = df.sort_values(by=col, ascending=asc)
                    msg = f"Sorted by '{col}'."

            elif action == 'delete_row':
                idx = params.get('index')
                if idx is not None and idx in df.index:
                    df = df.drop(idx).reset_index(drop=True)
                    msg = f"Deleted Row {idx}."

            elif action == 'delete_col':
                col = params.get('column')
                if col in df.columns:
                    df = df.drop(columns=[col])
                    msg = f"Deleted Column '{col}'."

            # --- 5. ANALYSIS (Fixed: Returns Text for File) ---
            elif action == 'analyze':
                col = params.get('column')
                if col:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        desc = df[col].describe()
                        stats_str = desc.to_string()
                        
                        msg = f"Analyzed {col}."
                        # Display on screen
                        st.text(f"--- Analysis: {col} ---\n{stats_str}")
                        
                        # Save to artifact for download
                        artifact = {
                            'type': 'text',
                            'content': f"ANALYSIS REPORT FOR '{col}':\n{stats_str}\n\n",
                            'filename': f"analysis_{col}.txt"
                        }
                    else:
                        msg = f"Column '{col}' is not numeric."

            # --- 6. PLOTTING (Fixed: Returns Image for File) ---
            elif action == 'plot':
                col = params.get('column')
                if col:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    plt.style.use('dark_background')
                    
                    if pd.api.types.is_numeric_dtype(df[col]):
                        sns.histplot(df[col], kde=True, ax=ax, color='#00ff41')
                        ax.set_title(f"Distribution of {col}")
                    else:
                        counts = df[col].value_counts().head(10)
                        sns.barplot(x=counts.index, y=counts.values, ax=ax, palette='viridis')
                        ax.set_title(f"Count of {col}")
                    
                    st.pyplot(fig) # Show on Monitor
                    
                    # Return Figure for Download
                    artifact = {
                        'type': 'plot',
                        'content': fig,
                        'filename': f"plot_{col}.png"
                    }
                    msg = f"Plot generated for '{col}'."

        except Exception as e:
            msg = f"Error: {str(e)}"
            
        return df, msg, artifact
