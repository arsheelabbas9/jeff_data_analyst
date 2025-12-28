"""
JEFF v5.0: DATA INTEGRITY VALIDATOR (PHASE 7)
----------------------------------------------
Role: Quality Assurance & Data Auditing

This module performs a deep-scan of the materialized DataFrame.
It identifies 'dirty data'—missing values, mixed types, and structural
anomalies—before the Execution Suite (Phase 8) begins analysis.
"""

import pandas as pd
import logging

class DataIntegrityValidator:
    def __init__(self):
        self.validation_report = {
            "missing_data": {},
            "type_mismatch": [],
            "status": "Incomplete"
        }

    def validate(self, df):
        """
        Runs a multi-point audit on the structured columns.
        """
        # Only validate columns the user can see (the clean ones)
        target_cols = [c for c in df.columns if not c.startswith('_')]
        
        if not target_cols:
            print("⚠️ Jeff: No structured columns found to validate.")
            return

        print("\n" + "🔍" * 15)
        print("PHASE 7: INTEGRITY AUDIT START")
        print("🔍" * 15)

        # 1. Null Value Detection (The 'Swiss Cheese' Check)
        for col in target_cols:
            null_count = df[col].isna().sum()
            if null_count > 0:
                self.validation_report["missing_data"][col] = null_count
                percentage = (null_count / len(df)) * 100
                print(f"📍 Column '{col}': {null_count} missing entries ({percentage:.1f}%)")

        # 2. Type Consistency Check
        # Ensures that a 'Numeric' column doesn't accidentally contain strings
        for col in target_cols:
            # Check the unique types in the column
            types = df[col].dropna().map(type).unique()
            if len(types) > 1:
                self.validation_report["type_mismatch"].append(col)
                print(f"📍 Column '{col}': Mixed data types detected {types}. This may cause errors in math.")

        # 3. Interactive Repair Suggestion
        self._provide_repair_options(df, target_cols)

        self.validation_report["status"] = "Verified"
        print("\n✅ Jeff: Integrity audit complete. Data is now locked for analysis.")

    def _provide_repair_options(self, df, target_cols):
        """
        Negotiates with the user to fix issues found during the audit.
        """
        if not self.validation_report["missing_data"]:
            return

        print("\n[Jeff]: I found some holes in your data.")
        print("1. Fill missing numbers with '0' and text with 'Unknown'")
        print("2. Drop rows containing missing data")
        print("3. Leave them as they are (None/NaN)")
        
        choice = input("\nHow should I proceed? (1/2/3) → ").strip()

        if choice == "1":
            for col in target_cols:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna("Unknown")
                else:
                    df[col] = df[col].fillna(0)
            print("✨ Jeff: Missing values filled.")
            
        elif choice == "2":
            before = len(df)
            df.dropna(subset=target_cols, inplace=True)
            after = len(df)
            print(f"✨ Jeff: Removed {before - after} rows containing errors.")
            
        else:
            print("ℹ️ Jeff: Proceeding with raw gaps.")

# Global Hook for Orchestrator Logic:
# DataIntegrityValidator().validate(self.df)