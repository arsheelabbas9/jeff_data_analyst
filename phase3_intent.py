"""
JEFF v8.6: COGNITIVE INTENT ENGINE (PHASE 3)
--------------------------------------------
UPDATED: Robust Renaming (Handles spaces in column names)
"""

import re
import difflib

class CognitiveIntentEngine:
    def __init__(self):
        self.intent_library = {
            "terminate": ["exit", "quit", "end"],
            "inspect": ["show", "view", "list", "see"],
            "update_val": ["update", "set", "modify", "correct"],
            "replace_global": ["replace", "swap", "substitute"],
            "fill_missing": ["fill missing", "fill null", "fill nan", "fill empty"],
            "scrub": ["clean", "proper case", "capitalize"],
            "dedupe": ["remove duplicates", "dedupe", "unique", "drop duplicates"],
            "rebrand": ["rename", "change header", "label", "change name"], # Target Intent
            "organize": ["sort", "arrange", "order"],
            "eliminate_col": ["delete column", "drop column", "remove column"],
            "eliminate_row": ["delete row", "drop row", "remove row"],
            "add_col": ["add column", "new column"],
            "add_row": ["add row", "new row"],
            "group_by": ["group by", "pivot", "aggregate"],
            "analytics": ["analyze", "stats", "summarize", "describe", "math"],
            "refine": ["filter", "where", "greater", "less"],
            "discovery": ["search", "find", "locate"],
            "visualize": ["plot", "chart", "graph"],
            "export": ["save", "export", "download"]
        }

    def _get_fuzzy_intent(self, user_word):
        all_keywords = [k for keys in self.intent_library.values() for k in keys]
        matches = difflib.get_close_matches(user_word, all_keywords, n=1, cutoff=0.7)
        if not matches: return None
        for action, keys in self.intent_library.items():
            if matches[0] in keys: return action
        return None

    def _extract_parameters(self, action, command):
        params = {}
        words = command.split()
        if len(words) > 1: params["target"] = words[-1]

        # --- PARSING LOGIC ---
        if action == "rebrand":
            # Logic: Split by ' to ' or ' as '
            # Command: "Rename Customer Name to Client Name"
            # Remove the action word first
            clean_cmd = re.sub(r'^(rename|change header|label|change name)\s+', '', command, flags=re.IGNORECASE)
            
            # Split
            parts = re.split(r'\s+to\s+|\s+as\s+', clean_cmd)
            
            if len(parts) >= 2:
                # Strip quotes if user added them
                params["old"] = parts[0].strip().strip("'").strip('"')
                params["new"] = parts[1].strip().strip("'").strip('"')
            else:
                # If user typed just "Rename", we leave params empty.
                # The GUI will detect this and launch Interactive Mode.
                pass

        elif action == "dedupe":
            if "by" in command: params["subset"] = command.split("by")[-1].strip()

        elif action == "update_val":
            if "where" in command:
                parts = command.split("where")
                left, right = parts[0], parts[1]
                if " to " in left:
                    l_parts = left.split(" to ")
                    params["target_col"] = l_parts[0].replace("update", "").strip()
                    params["new_val"] = l_parts[1].strip()
                cond_match = re.split(r'\s+(?:is|=|==)\s+', right.strip())
                if len(cond_match) >= 2:
                    params["cond_col"], params["cond_val"] = cond_match[0].strip(), cond_match[1].strip()
            elif "row" in command and "to" in command:
                match = re.search(r'row\s+(\d+)\s+(.+)\s+to\s+(.+)', command)
                if match:
                    params["row_index"], params["target_col"], params["new_val"] = int(match.group(1)), match.group(2).strip(), match.group(3).strip()

        elif action == "replace_global":
            match = re.search(r"replace\s+(.+)\s+with\s+(.+)", command)
            if match:
                params["old_val"] = match.group(1).strip().strip("'").strip('"')
                params["new_val"] = match.group(2).strip().strip("'").strip('"')

        elif action == "fill_missing":
            match = re.search(r"in\s+(.+)\s+with\s+(.+)", command)
            if match: params["col"], params["val"] = match.group(1).strip(), match.group(2).strip()

        elif action == "group_by":
            math_ops = ["sum", "mean", "average", "count", "max", "min"]
            found_op = next((op for op in math_ops if op in command), "count")
            parts = command.replace("group by", "").split(found_op)
            if len(parts) >= 1:
                params["group_col"], params["agg_col"], params["op"] = parts[0].strip(), parts[1].strip() if len(parts) > 1 else None, found_op

        elif action == "refine":
            match = re.search(r'(\w+)\s*([><=]+)\s*(.+)', command)
            if match: params["col"], params["op"], params["val"] = match.group(1), match.group(2), match.group(3)

        elif action == "organize":
            params["direction"] = "desc" if "desc" in command else "asc"
            params["target"] = command.replace("sort", "").replace("by", "").replace("desc", "").replace("asc", "").strip()

        elif action == "add_col":
            parts = command.split()
            if len(parts) >= 3: params["name"], params["value"] = parts[2], parts[3] if len(parts)>3 else 0

        elif action == "add_row":
            data = command.replace("add row", "").strip()
            params["values"] = [x.strip() for x in data.split(',')]

        elif action == "eliminate_row":
            idx = re.findall(r'\d+', command)
            if idx: params["index"] = int(idx[0])

        return params

    def analyze_command(self, command, df_columns):
        cmd = command.lower().strip()
        intent = {"action": "unknown", "parameters": {}, "suggestions": []}
        
        for action, keys in self.intent_library.items():
            if any(k in cmd for k in keys):
                intent["action"] = action
                break
        
        if intent["action"] == "unknown":
            guess = self._get_fuzzy_intent(cmd.split()[0])
            if guess:
                intent["action"] = guess
                intent["suggestions"].append(f"Did you mean '{guess}'?")

        if intent["action"] != "unknown":
            intent["parameters"] = self._extract_parameters(intent["action"], cmd)
        
        return intent