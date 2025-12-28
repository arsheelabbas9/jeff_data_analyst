"""
JEFF v5.2: DYNAMIC AI ORCHESTRATOR
----------------------------------
Role: Intelligent Schema Negotiation & Dynamic Labeling
"""

import os
from phase5_schema import SchemaInferenceEngine
from phase6_materializer import DataMaterializer
from phase7_validation import DataIntegrityValidator
from phase9_finalize import SchemaLockMaster
from phase10_export import ProfessionalExporter

class AnalysisOrchestrator:
    def __init__(self, ingestor, intent_engine, action_suite):
        self.ingestor = ingestor
        self.intent_engine = intent_engine
        self.action_suite = action_suite
        self.df = None
        self.session_active = True

    def _dynamic_labeler(self):
        """
        AI Logic: Analyzes data values to assign probable headers 
        dynamically rather than hardcoding names.
        """
        new_names = {}
        for col in self.df.columns:
            if col.startswith("text_col"):
                sample = self.df[col].dropna().astype(str).tolist()
                # If values look like Cities (usually one word, proper case)
                if all(len(s.split()) == 1 for s in sample[:3]):
                    new_names[col] = "Location"
                # If values look like Names (usually two words)
                elif any(len(s.split()) >= 2 for s in sample[:3]):
                    new_names[col] = "Entity_Name"
            
            elif col.startswith("num_col"):
                mean_val = self.df[col].mean()
                # If numbers are large, likely Salary/Price
                if mean_val > 1000:
                    new_names[col] = "Value_Amt"
                # If numbers are small/sequential, likely ID
                elif mean_val < 1000:
                    new_names[col] = "ID_Ref"
        
        if new_names:
            self.df = self.df.rename(columns=new_names)
            print(f"🧠 Jeff AI: Dynamically identified headers: {list(new_names.values())}")

    def negotiate_schema(self):
        """Automatically applies structure and runs the Dynamic Labeler."""
        engine = SchemaInferenceEngine()
        suggested_schema = engine.infer(self.df)
        
        print("\n[Jeff]: 🧠 Patterns detected. Applying structure and identifying labels...")
        
        # Build the table
        self.df = DataMaterializer().materialize(self.df, suggested_schema)
        
        # Run AI Labeler (Not hardcoded!)
        self._dynamic_labeler()
        
        DataIntegrityValidator().validate(self.df)
        self.df = SchemaLockMaster().lock(self.df, suggested_schema)

    def start_session(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("🤖 JEFF: ANALYST READY")
        print("Paste data + type 'END'.")

        buffer = []
        while True:
            line = input("> ")
            if line.strip().upper() == "END": break
            buffer.append(line)

        if not buffer: return

        self.df = self.ingestor.build_diagnostic_dataframe("\n".join(buffer))
        self.negotiate_schema()
        self.run_command_loop()

    def run_command_loop(self):
        print("\n[Jeff]: Ready. Use identified labels for commands.")
        while self.session_active:
            try:
                user_input = input("\n[Analyst Mode] → ").strip()
                if not user_input: continue

                intent = self.intent_engine.analyze_command(user_input, self.df)
                if intent["action"] == "terminate": break

                self.df = self.action_suite.execute(intent, self.df)
                
                clean_cols = [c for c in self.df.columns if not str(c).startswith('_')]
                print("\n" + self.df[clean_cols].to_string(index=False))

            except Exception as e:
                print(f"⚠️ Error: {e}")

        ProfessionalExporter().save(self.df)