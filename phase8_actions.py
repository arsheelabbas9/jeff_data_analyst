import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

class ExecutionActionSuite:
    def execute(self, intent, df):
        action = intent['action']
        params = intent['parameters']
        msg = "Action completed."
        
        try:
            # --- 1. EDITING ---
            if action == 'update':
                if 'row_index' in params and 'column' in params:
                    # Update by Row Index: "Update Row 5 Name to Batman"
                    idx = params['row_index']
                    col = params['column']
                    val = params.get('value')
                    if idx in df.index:
                        df.at[idx, col] = val
                        msg = f"Updated Row {idx}, Column '{col}' to '{val}'"
                
                elif 'id_val' in params and 'column' in params:
                    # Update by ID: "Update Salary to 5000 where ID is 1"
                    # Assumes there is a column roughly named 'id'
                    id_val = params['id_val']
                    col = params['column']
                    val = params.get('value')
                    
                    # Find the ID column
                    id_col = next((c for c in df.columns if 'id' in c.lower()), None)
                    if id_col:
                        mask = df[id_col] == id_val
                        df.loc[mask, col] = val
                        msg = f"Updated '{col}' to '{val}' where {id_col} is {id_val}"
                    else:
                        msg = "Could not find an 'ID' column."

            # --- 2. CLEANING ---
            elif action == 'fill':
                col = params.get('column')
                val = params.get('value')
                if col and val:
                    # Try to convert to number if possible
                    try: val = float(val) 
                    except: pass
                    df[col] = df[col].fillna(val)
                    msg = f"Filled missing values in '{col}' with {val}"
            
            elif action == 'replace':
                old_val = params.get('old')
                new_val = params.get('new')
                if old_val and new_val:
                    df = df.replace(old_val, new_val, regex=False)
                    msg = f"Replaced '{old_val}' with '{new_val}' globally."

            elif action == 'dedupe':
                before = len(df)
                df = df.drop_duplicates()
                after = len(df)
                msg = f"Removed {before - after} duplicate rows."

            # --- 3. STRUCTURE ---
            elif action == 'rename':
                old = params.get('old_name')
                new = params.get('new_name')
                # Fuzzy match for old name if exact match fails
                real_old = next((c for c in df.columns if old.lower() == c.lower()), old)
                
                if real_old in df.columns:
                    df = df.rename(columns={real_old: new})
                    msg = f"Renamed column '{real_old}' to '{new}'."
                else:
                    msg = f"Column '{old}' not found."

            elif action == 'delete_row':
                idx = params.get('index')
                if idx is not None and idx in df.index:
                    df = df.drop(idx)
                    df = df.reset_index(drop=True)
                    msg = f"Deleted Row {idx}."

            elif action == 'delete_col':
                col = params.get('column')
                if col in df.columns:
                    df = df.drop(columns=[col])
                    msg = f"Deleted Column '{col}'."

            # --- 4. DATA & ANALYSIS ---
            elif action == 'sort':
                col = params.get('column')
                asc = params.get('ascending', True)
                if col:
                    df = df.sort_values(by=col, ascending=asc)
                    msg = f"Sorted by '{col}' ({'Ascending' if asc else 'Descending'})."

            elif action == 'filter':
                col = params.get('column')
                op = params.get('operator')
                val = params.get('value')
                
                if col and op and val:
                    try: val = float(val)
                    except: pass # keep as string
                    
                    if op == '>':
                        df = df[df[col] > val]
                    elif op == '<':
                        df = df[df[col] < val]
                    
                    msg = f"Filtered {col} {op} {val}. {len(df)} rows remain."

            elif action == 'group':
                grp = params.get('group_col')
                agg_col = params.get('agg_col')
                func = params.get('agg', 'sum')
                
                if grp and agg_col:
                    # We perform the groupby but don't overwrite the main DF structure 
                    # unless user wants to pivot. For this Analyst tool, 
                    # usually users want to SEE the result.
                    # We will overwrite df to show the result.
                    df = df.groupby(grp)[agg_col].agg(func).reset_index()
                    msg = f"Grouped by {grp}, {func} of {agg_col}."

            elif action == 'analyze':
                col = params.get('column')
                if col:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        desc = df[col].describe()
                        msg = f"STATS for {col}: Mean={desc['mean']:.2f}, Max={desc['max']}, Min={desc['min']}"
                        st.info(msg) # Show sticky banner
                    else:
                        msg = f"Column '{col}' is not numeric."

            # --- 5. PLOTTING (The Missing Feature) ---
            elif action == 'plot':
                col = params.get('column')
                if col:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        fig, ax = plt.subplots(figsize=(8, 4))
                        # Dark Theme Plot
                        plt.style.use('dark_background')
                        sns.histplot(df[col], kde=True, ax=ax, color='#3b8ed0')
                        ax.set_title(f"Distribution of {col}", color='white')
                        ax.grid(color='#333')
                        
                        # Render directly to Streamlit
                        st.pyplot(fig)
                        msg = f"Generated Histogram for '{col}'."
                    else:
                        # Categorical Bar Plot
                        counts = df[col].value_counts().head(10)
                        fig, ax = plt.subplots(figsize=(8, 4))
                        plt.style.use('dark_background')
                        sns.barplot(x=counts.index, y=counts.values, ax=ax, palette='Blues_d')
                        ax.set_title(f"Top 10 Counts: {col}", color='white')
                        st.pyplot(fig)
                        msg = f"Generated Bar Chart for '{col}'."

        except Exception as e:
            msg = f"Error executing {action}: {str(e)}"

        return df, msg
