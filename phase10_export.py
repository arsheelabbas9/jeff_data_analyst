"""
JEFF v6.1: PROFESSIONAL EXPORT ENGINE (PHASE 10)
------------------------------------------------
UPDATED: Conflict Detection (Prevents Overwriting)
"""

import pandas as pd
import os
import logging

class ProfessionalExporter:
    def __init__(self):
        self.output_directory = os.getcwd()

    def save(self, df, filename):
        """
        Saves DataFrame to Excel with safety checks.
        Returns: Success Message, Error Message, or 'FILE_EXISTS' status.
        """
        if df is None or df.empty:
            return "❌ No data to export."

        # Auto-append extension if missing
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'

        full_path = os.path.join(self.output_directory, filename)

        # --- SAFETY CHECK ---
        if os.path.exists(full_path):
            return "FILE_EXISTS"

        # --- CLEAN & SAVE ---
        # Remove internal Jeff columns (starting with _)
        clean_cols = [col for col in df.columns if not str(col).startswith('_')]
        export_df = df[clean_cols].copy()

        try:
            export_df.to_excel(full_path, index=False, engine='openpyxl')
            logging.info(f"Exported to {full_path}")
            return f"✅ Success! Saved as: {filename}"
        
        except PermissionError:
            return f"❌ Error: The file '{filename}' is open. Close it and try again."
        except Exception as e:
            return f"❌ Critical Error: {str(e)}"