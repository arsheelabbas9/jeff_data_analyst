"""
JEFF v5.0: DATA MATERIALIZER (PHASE 6)
--------------------------------------
Role: Structural Transformation & Defensive Extraction

This module executes the schema blueprint. It transforms hidden 
list-data into first-class DataFrame columns while preventing 
IndexErrors through defensive boundary checking.
"""

import pandas as pd
import logging

class DataMaterializer:
    def __init__(self):
        self.error_count = 0

    def _safe_extract(self, row, key, index):
        """
        Safely retrieves a value from a list within a row.
        If the index is out of bounds, it returns None instead of crashing.
        """
        try:
            target_list = row[key]
            if index < len(target_list):
                return target_list[index]
            return None
        except Exception as e:
            self.error_count += 1
            return None

    def materialize(self, df, schema):
        """
        Physically creates new columns in the DataFrame based on the schema.
        
        Args:
            df (pd.DataFrame): The diagnostic dataframe from Phase 2.
            schema (list): The suggested columns from Phase 5.
        """
        if not schema:
            logging.info("Materializer: No schema provided. Skipping transformation.")
            return df

        # Work on a copy to preserve original diagnostic data
        materialized_df = df.copy()

        print(f"\n[Jeff]: 🏗️  Materializing {len(schema)} columns...")

        for col_blueprint in schema:
            col_name = col_blueprint["name"]
            source_info = col_blueprint["source"] # Example: "_strings[0]"
            
            # Parse the source string to identify the key and index
            # Extracting 'strings' from '_strings[0]' and '0' from '[0]'
            try:
                list_key = "_" + source_info.split("[")[0].split("_")[1]
                idx = int(source_info.split("[")[1].split("]")[0])
                
                # Apply safe extraction to every row
                materialized_df[col_name] = materialized_df.apply(
                    lambda row: self._safe_extract(row, list_key, idx), 
                    axis=1
                )
                
            except Exception as e:
                print(f"⚠️ Materializer Error on column '{col_name}': {e}")
                logging.error(f"Mapping error for {col_name}: {e}")

        if self.error_count > 0:
            print(f"ℹ️ Jeff: Materialization complete with {self.error_count} boundary adjustments.")
        
        # Reorder: Put the new columns at the front, keep hidden columns at the back
        new_cols = [s["name"] for s in schema]
        internal_cols = [c for c in materialized_df.columns if c.startswith("_")]
        
        return materialized_df[new_cols + internal_cols]

# Logic Check for Phase 4:
# The Orchestrator calls: self.df = DataMaterializer().materialize(self.df, schema)