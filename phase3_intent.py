import re

class CognitiveIntentEngine:
    def __init__(self):
        self.intent_map = {
            'add_row': ['add row', 'insert row', 'new row', 'append row'],
            'add_col': ['add column', 'insert column', 'new column', 'add col'],
            'update': ['update', 'change', 'set', 'modify'],
            'fill': ['fill', 'impute', 'replace missing', 'nan'],
            'replace': ['replace', 'swap', 'substitute'],
            'dedupe': ['dedupe', 'remove duplicates', 'unique', 'distinct'],
            'delete_row': ['delete row', 'drop row', 'remove row'],
            'delete_col': ['delete column', 'drop column', 'remove column', 'delete col'],
            'rename': ['rename', 'change column', 'change header'],
            'group': ['group by', 'pivot', 'summarize'],
            'sort': ['sort', 'order by', 'arrange'],
            'filter': ['filter', 'keep', 'where', 'show only'],
            'analyze': ['analyze', 'stats', 'describe', 'summary', 'statistics'],
            'plot': ['plot', 'graph', 'chart', 'visualize', 'histogram', 'bar']
        }

    def analyze_command(self, user_text, columns):
        text = user_text.lower().strip()
        found_action = "unknown"
        
        # 1. Detect Action
        for action, keywords in self.intent_map.items():
            if any(k in text for k in keywords):
                found_action = action
                # Prioritize 'add_col' over 'add_row' if ambiguity exists, but usually distinct
                break
        
        # 2. Extract Parameters
        params = {}
        
        # --- NEW: ADD STRUCTURE ---
        if found_action == 'add_col':
            # "Add column Status" -> extract "Status"
            # Remove the keywords to find the name
            clean_text = text
            for k in self.intent_map['add_col']:
                clean_text = clean_text.replace(k, "")
            
            # The remaining text (stripped) is likely the column name
            col_name = clean_text.strip().title() # Default to Title Case
            if col_name:
                params['column'] = col_name

        elif found_action == 'add_row':
            # "Add row" usually implies appending a blank one, 
            # unless complex parsing is done. We keep it simple.
            params['index'] = -1 # Indicator for append

        # --- DEDUPE (Fixed) ---
        elif found_action == 'dedupe':
            # Check if user specified a column: "Dedupe by Email"
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        # --- UPDATE (Fixed) ---
        elif found_action == 'update':
            # Improved Regex to capture value: "to 'New Value'" or "to 500"
            # Captures text after 'to' until end of string or ' in row'
            val_match = re.search(r"to\s+['\"]?(.+?)['\"]?(?:\s+in\s+row|\s+at\s+index|$)", text)
            if val_match:
                params['value'] = val_match.group(1).strip()
            
            # Row Index
            row_match = re.search(r"(?:row|index)\s+(\d+)", text)
            if row_match:
                params['row_index'] = int(row_match.group(1))
            
            # ID condition
            id_match = re.search(r"id\s+(?:is|=)\s+(\d+)", text)
            if id_match:
                params['id_val'] = int(id_match.group(1))

            # Column Name
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    # If value wasn't found via regex (e.g., "Update Salary 5000"), try strict proximity?
                    # For now, regex 'to' is safest.

        # --- ANALYSIS & PLOTS ---
        elif found_action in ['analyze', 'plot']:
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        # --- STANDARD OPERATIONS ---
        elif found_action == 'delete_row':
            match = re.search(r"row\s+(\d+)", text)
            if match: params['index'] = int(match.group(1))
                
        elif found_action == 'delete_col':
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        elif found_action == 'rename':
            match = re.search(r"rename\s+['\"]?(.+?)['\"]?\s+to\s+['\"]?(.+?)['\"]?$", text)
            if match:
                params['old_name'] = match.group(1)
                params['new_name'] = match.group(2)

        elif found_action == 'fill':
            val_match = re.search(r"with\s+([\w\d\.]+)", text)
            if val_match: params['value'] = val_match.group(1)
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        elif found_action == 'filter':
            # Simple operators
            if '>' in text:
                params['operator'] = '>'
                params['value'] = text.split('>')[1].strip()
            elif '<' in text:
                params['operator'] = '<'
                params['value'] = text.split('<')[1].strip()
            elif '=' in text:
                params['operator'] = '=='
                params['value'] = text.split('=')[1].strip()
            
            for col in columns:
                if col.lower() in text:
                    params['column'] = col

        return {
            "action": found_action,
            "parameters": params,
            "suggestions": []
        }
