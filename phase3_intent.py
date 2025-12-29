import re

class CognitiveIntentEngine:
    def __init__(self):
        self.intent_map = {
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
                break
        
        # 2. Extract Parameters
        params = {}
        
        # --- PLOTTING ---
        if found_action == 'plot':
            # Find which column to plot
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break
        
        # --- RENAMING ---
        elif found_action == 'rename':
            # Look for: Rename 'Old' to 'New'
            # regex to capture text inside quotes or simple words
            match = re.search(r"rename\s+['\"]?([\w\s]+)['\"]?\s+to\s+['\"]?([\w\s]+)['\"]?", text)
            if match:
                params['old_name'] = match.group(1)
                params['new_name'] = match.group(2)
        
        # --- ANALYSIS ---
        elif found_action == 'analyze':
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        # --- UPDATE ---
        elif found_action == 'update':
            # Heuristic: "Update Salary to 5000..."
            val_match = re.search(r"to\s+['\"]?([\w\.]+)", text)
            if val_match:
                params['value'] = val_match.group(1)
            
            # Check for Row index
            row_match = re.search(r"row\s+(\d+)", text)
            if row_match:
                params['row_index'] = int(row_match.group(1))
            
            # Check for ID condition "where ID is 5"
            id_match = re.search(r"id\s+(?:is|=)\s+(\d+)", text)
            if id_match:
                params['id_val'] = int(id_match.group(1))

            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    # Don't break immediately, might overlap
        
        # --- DELETION ---
        elif found_action == 'delete_row':
            match = re.search(r"row\s+(\d+)", text)
            if match:
                params['index'] = int(match.group(1))
                
        elif found_action == 'delete_col':
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        # --- SORTING ---
        elif found_action == 'sort':
            params['ascending'] = 'desc' not in text
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        # --- FILTERING ---
        elif found_action == 'filter':
            # Look for > < =
            if '>' in text:
                parts = text.split('>')
                params['operator'] = '>'
                params['value'] = parts[1].strip()
            elif '<' in text:
                parts = text.split('<')
                params['operator'] = '<'
                params['value'] = parts[1].strip()
            
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break
        
        # --- CLEANING ---
        elif found_action == 'fill':
            val_match = re.search(r"with\s+([\w\d\.]+)", text)
            if val_match:
                params['value'] = val_match.group(1)
            for col in columns:
                if col.lower() in text:
                    params['column'] = col
                    break

        elif found_action == 'replace':
            # Replace 'A' with 'B'
            match = re.search(r"replace\s+['\"]?(.+?)['\"]?\s+with\s+['\"]?(.+?)['\"]?$", text)
            if match:
                params['old'] = match.group(1)
                params['new'] = match.group(2)
        
        # --- GROUPING ---
        elif found_action == 'group':
            # "Group by City sum Sales"
            for col in columns:
                if col.lower() in text:
                    if 'group_col' not in params:
                        params['group_col'] = col # First col found is grouper
                    else:
                        params['agg_col'] = col # Second is target
            
            if 'sum' in text: params['agg'] = 'sum'
            elif 'mean' in text or 'average' in text: params['agg'] = 'mean'
            elif 'count' in text: params['agg'] = 'count'
            else: params['agg'] = 'sum' # default

        return {
            "action": found_action,
            "parameters": params,
            "suggestions": []
        }
