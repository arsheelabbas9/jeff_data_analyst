"""
JEFF v5.5: NEURAL INGEST ENGINE (PHASE 2)
-----------------------------------------
UPDATED: Compound Number Support (ninety-two) & Hyphen Handling
"""

import re
import pandas as pd
import logging

class NeuralIngestor:
    def __init__(self):
        # Full linguistic dictionary
        self.num_words = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
            'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
            'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
            'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80,
            'ninety': 90, 'hundred': 100, 'thousand': 1000, 'million': 1000000,
            'k': 1000, 'm': 1000000 # Slang support
        }
        self.junk_labels = r'(?i)\b(id|name|val|qty|total|price|entry|record|header|user):'

    def text_to_numeric(self, text):
        """
        Converts 'ninety-two' -> 92.0
        """
        text = text.lower().strip()
        # FIX: Replace hyphens with spaces for compound numbers (ninety-two -> ninety two)
        text = text.replace("-", " ")
        
        if not text: return None
            
        parts = text.split()
        total = 0
        current = 0
        found_word = False
        
        for word in parts:
            if word in self.num_words:
                found_word = True
                val = self.num_words[word]
                if val == 100:
                    current = (current if current > 0 else 1) * 100
                elif val >= 1000:
                    total += (current if current > 0 else 1) * val
                    current = 0
                else:
                    current += val
            else:
                # If a word isn't a number (and we haven't found a number yet), keep looking
                continue
        
        result = total + current
        return float(result) if found_word else None

    def fuzzy_tokenize(self, line):
        line = re.sub(r'"([^"]+)"', lambda m: m.group(1).replace(" ", "___"), line)
        line = re.sub(self.junk_labels, ' ', line)
        tokens = re.split(r"[,\|:=\t\s]+", line)
        clean_tokens = [t.replace("___", " ").strip() for t in tokens if t.strip()]
        return clean_tokens

    def analyze_line_composition(self, line):
        tokens = self.fuzzy_tokenize(line)
        numeric_data = []
        string_data = []
        
        for t in tokens:
            try:
                numeric_data.append(float(t))
                continue
            except ValueError:
                pass
            
            # Use updated logic
            linguistic_val = self.text_to_numeric(t)
            if linguistic_val is not None:
                numeric_data.append(linguistic_val)
            else:
                string_data.append(t)
                
        return {
            "_raw": line, "_tokens": tokens,
            "_strings": string_data, "_numbers": numeric_data,
            "_token_count": len(tokens)
        }

    def build_diagnostic_dataframe(self, raw_text):
        if not raw_text.strip(): return pd.DataFrame()
        line_data = [self.analyze_line_composition(line) for line in raw_text.splitlines() if line.strip()]
        return pd.DataFrame(line_data)