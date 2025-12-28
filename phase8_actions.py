"""
JEFF v8.5: EXECUTION ACTION SUITE (PHASE 8)
-------------------------------------------
UPDATED: Returns (DataFrame, Message) for GUI Feedback
"""

import pandas as pd
import matplotlib.pyplot as plt

class ExecutionActionSuite:
    def _smart_type(self, val):
        try: return float(val)
        except: return val

    def _find_col(self, df, name):
        if not name: return None
        return next((c for c in df.columns if c.lower() == str(name).lower()), None)

    def execute(self, intent, df):
        action = intent["action"]
        params = intent["parameters"]
        msg = "✅ Action Complete."
        
        try:
            # --- DEDUPE (ROBUST) ---
            if action == "dedupe":
                # Defaults handled by GUI, but Phase 8 executes logic
                keep_strat = params.get("keep", "first")
                subset = params.get("subset")
                
                start_len = len(df)
                
                # Resolve subset column if provided
                if subset:
                    actual_subset = self._find_col(df, subset)
                    if actual_subset:
                        df = df.drop_duplicates(subset=[actual_subset], keep=keep_strat)
                    else:
                        return df, f"❌ Error: Column '{subset}' not found for deduplication."
                else:
                    df = df.drop_duplicates(keep=keep_strat)
                
                removed = start_len - len(df)
                msg = f"♻️ Dedupe Complete. Removed {removed} rows (Strategy: Keep {keep_strat})."

            # --- JOB 1: UPDATES ---
            elif action == "update_val":
                target_col = params.get("target_col")
                new_val = self._smart_type(params.get("new_val"))
                
                if "row_index" in params:
                    idx = params["row_index"]
                    actual_col = self._find_col(df, target_col)
                    if idx in df.index and actual_col:
                        df.at[idx, actual_col] = new_val
                        msg = f"✅ Updated Row {idx} [{actual_col}] to '{new_val}'."
                    else: return df, "❌ Invalid Row Index or Column."
                elif "cond_col" in params:
                    cond_col, cond_val = params["cond_col"], self._smart_type(params["cond_val"])
                    actual_t, actual_c = self._find_col(df, target_col), self._find_col(df, cond_col)
                    if actual_t and actual_c:
                        mask = df[actual_c] == cond_val
                        count = mask.sum()
                        if count > 0:
                            df.loc[mask, actual_t] = new_val
                            msg = f"✅ Updated {count} rows where {actual_c} is {cond_val}."
                        else: return df, "⚠️ No matches found for that condition."
                    else: return df, f"❌ Columns '{target_col}' or '{cond_col}' not found."

            elif action == "replace_global":
                old, new = self._smart_type(params.get("old_val")), self._smart_type(params.get("new_val"))
                df = df.replace(old, new)
                msg = f"✅ Replaced all instances of '{old}' with '{new}'."

            # --- JOB 2: CLEANING ---
            elif action == "fill_missing":
                col, val = params.get("col"), self._smart_type(params.get("val"))
                actual_col = self._find_col(df, col)
                if actual_col:
                    df[actual_col] = df[actual_col].fillna(val)
                    msg = f"✅ Filled missing values in '{actual_col}' with '{val}'."
                else: return df, f"❌ Column '{col}' not found."

            elif action == "scrub":
                target = params.get("target")
                actual_col = self._find_col(df, target)
                if actual_col:
                    df[actual_col] = df[actual_col].astype(str).str.title().str.strip()
                    msg = f"✨ Scrubbed format of '{actual_col}'."
                else: return df, f"❌ Column '{target}' not found."

            # --- JOB 3: STRUCTURE ---
            elif action == "organize":
                target = params.get("target")
                asc = params.get("direction") == "asc"
                actual_col = self._find_col(df, target)
                if actual_col: 
                    df = df.sort_values(by=actual_col, ascending=asc)
                    msg = f"✅ Sorted by {actual_col} ({'Asc' if asc else 'Desc'})."
                else: return df, f"❌ Column '{target}' not found."

            elif action == "rebrand":
                old, new = params.get("old"), params.get("new")
                actual_col = self._find_col(df, old)
                if actual_col: 
                    df = df.rename(columns={actual_col: new})
                    msg = f"✅ Renamed '{old}' to '{new}'."
                else: return df, f"❌ Column '{old}' not found."

            elif action == "eliminate_col":
                actual_col = self._find_col(df, params.get("target"))
                if actual_col: 
                    df = df.drop(columns=[actual_col])
                    msg = f"🗑️ Deleted column '{actual_col}'."
                else: return df, f"❌ Column '{params.get('target')}' not found."

            elif action == "eliminate_row":
                idx = params.get("index")
                if idx in df.index: 
                    df = df.drop(index=idx)
                    msg = f"🗑️ Deleted row {idx}."
                else: return df, f"❌ Row index {idx} not found."

            elif action == "add_col":
                df[params["name"]] = self._smart_type(params["value"])
                msg = f"✨ Added column '{params['name']}'."

            elif action == "add_row":
                vals = [self._smart_type(x) for x in params.get("values", [])]
                if len(vals) < len(df.columns): vals += [None]*(len(df.columns)-len(vals))
                df.loc[len(df)] = vals[:len(df.columns)]
                msg = "✨ Added new row."

            # --- JOB 4: ANALYSIS (RETURNS STRING RESULT) ---
            elif action == "group_by":
                group_col = self._find_col(df, params.get("group_col"))
                agg_col = self._find_col(df, params.get("agg_col"))
                op = params.get("op", "count")
                if group_col and agg_col:
                    res = df.groupby(group_col)[agg_col].agg(op)
                    # We return the original DF, but the Message contains the analysis
                    msg = f"📊 GROUP BY RESULTS ({op}):\n{res.to_string()}"
                else: return df, "❌ Columns not found for grouping."

            elif action == "analytics":
                msg = f"📊 DATA SUMMARY:\n{df.describe().T.to_string()}"

            elif action == "refine":
                col, op, val = params.get("col"), params.get("op"), params.get("val")
                actual_col = self._find_col(df, col)
                if actual_col:
                    try: 
                        df = df.query(f"`{actual_col}` {op} {val}")
                        msg = f"✅ Filtered data. {len(df)} rows remaining."
                    except: 
                        df = df.query(f"`{actual_col}` {op} '{val}'")
                        msg = f"✅ Filtered data. {len(df)} rows remaining."
                else: return df, f"❌ Column '{col}' not found."

            elif action == "discovery":
                term = params.get("target", "").lower()
                # Just return a message, maybe filter in future?
                msg = f"🔍 Search feature active. Use Filter to isolate '{term}'."

            elif action == "visualize":
                target = self._find_col(df, params.get("target"))
                if target:
                    plt.figure(figsize=(8, 4))
                    if df[target].dtype == 'object': df[target].value_counts().head(10).plot(kind='bar')
                    else: df[target].plot(kind='hist', bins=10)
                    plt.title(f"Analysis of {target}")
                    plt.show()
                    msg = f"📈 Chart generated for {target}."
                else: return df, f"❌ Column '{params.get('target')}' not found."

        except Exception as e:
            return df, f"⚠️ Critical Action Error: {str(e)}"

        return df, msg