"""
JEFF v5.0: SCHEMA INFERENCE ENGINE (PHASE 5)
--------------------------------------------
Role: Pattern Recognition & Structural Blueprinting

This module scans diagnostic data to find consistent columns.
It calculates confidence scores based on data presence (Fill Rate)
to ensure suggested schemas are accurate and robust.
"""

import logging

class SchemaInferenceEngine:
    def __init__(self):
        # Configuration for "Commercial Grade" thresholds
        self.MIN_CONFIDENCE = 0.5  # 50% fill rate required to suggest a column
        self.LABEL_MAX_LEN = 3     # Strings shorter than this are treated as junk labels

    def infer(self, df):
        """
        Scans the Diagnostic DataFrame and returns a list of suggested columns.
        Each column includes a 'name', 'source', and 'confidence' score.
        """
        if df.empty:
            logging.warning("Schema Engine: Attempted inference on empty DataFrame.")
            return []

        suggested_schema = []

        # 1. Analyze String Columns (_strings)
        if not df["_strings"].empty:
            # Find the widest row to determine max possible string columns
            max_str_width = df["_strings"].map(len).max()
            
            for i in range(max_str_width):
                # Sample all values at this specific index across all rows
                vals = df["_strings"].map(lambda x: x[i] if len(x) > i else None)
                
                # Calculate Fill Rate (Confidence)
                fill_rate = vals.notna().mean()
                
                # Logic: Ignore indices that are mostly empty or contain short junk labels (like "ID:")
                # This prevents the "Shifted Column" bug seen in previous versions.
                is_label = vals.dropna().map(lambda x: len(str(x)) <= self.LABEL_MAX_LEN).mean() > 0.7
                
                if fill_rate >= self.MIN_CONFIDENCE and not is_label:
                    suggested_schema.append({
                        "name": f"text_col_{i}",
                        "source": f"_strings[{i}]",
                        "confidence": round(fill_rate, 2),
                        "type": "string"
                    })

        # 2. Analyze Numeric Columns (_numbers)
        if not df["_numbers"].empty:
            max_num_width = df["_numbers"].map(len).max()
            
            for i in range(max_num_width):
                vals = df["_numbers"].map(lambda x: x[i] if len(x) > i else None)
                fill_rate = vals.notna().mean()
                
                if fill_rate >= self.MIN_CONFIDENCE:
                    suggested_schema.append({
                        "name": f"num_col_{i}",
                        "source": f"_numbers[{i}]",
                        "confidence": round(fill_rate, 2),
                        "type": "numeric"
                    })

        return suggested_schema

    def present(self, schema):
        """
        Interactive Phase: Presents the blueprint to the user for approval.
        As defined in Phase 4 Orchestration negotiation.
        """
        if not schema:
            print("\n[Jeff]: 🔍 No clear patterns found. Data might be too unstructured.")
            return "skip"

        print("\n" + "═"*45)
        print("🧠 JEFF'S SUGGESTED DATA STRUCTURE")
        print("═"*45)
        print(f"{'SUGGESTED NAME':<15} | {'SOURCE':<12} | {'CONFIDENCE'}")
        print("-" * 45)

        for s in schema:
            conf_percent = f"{int(s['confidence'] * 100)}%"
            print(f"{s['name']:<15} | {s['source']:<12} | {conf_percent}")

        print("-" * 45)
        print("\n[Choice 1]: Apply structure (Unlock Analysis Features)")
        print("[Choice 2]: Skip (Stay in Raw Diagnostic Mode)")
        
        choice = input("\nSelect (1/2) → ").strip()
        return "apply" if choice == "1" else "skip"