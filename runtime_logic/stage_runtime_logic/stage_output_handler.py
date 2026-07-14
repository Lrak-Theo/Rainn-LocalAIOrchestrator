import json
from integrations.chart_renderer import render_chart_svg


class OutputHandler:
    # Output Hanlder reads the output text and figures out what format the output is in

    @staticmethod
    # Desired_output_type is the desireable option for handling the output
    def desired_output_type(stage_type, stage_description):

        # haystack refers to the concatenated string of the stage meant for key word findings in one string
        haystack = f"{stage_type.lower()} {stage_description.lower()}"

        # A dict for file extensions with a list of likely words that relates to the extension
        keywords = {
            "svg":  ["graph", "visual", "chart", "diagram", "visualize", "plot", "infographic"],
            "csv":  ["csv", "table", "spreadsheet", "tabular", "rows", "columns", "export"],
            "json": ["json", "structured", "schema", "key-value", "object", "array", "fields"]
        } 

        # Loop to pick the output format by keyword match, with keyword.items() creating the a dict looop
        for output_type, words in keywords.items():
            if any(w in haystack for w in words):
                # Retrun the found output type
                return output_type

        return None

    @staticmethod
    # If desired_output_type returns None, infer_output_type is the fallback
    def infer_output_type(output_text):

        # Strip leading whitespace so format markers appear at the start
        text = (output_text or "").lstrip() 

        # Only need the first 500 chars — format is always declared at the top
        text_lower = text[:500].lower()

        # SVG can start directly with <svg or with an XML declaration first
        if text_lower.startswith("<svg") or ("<svg" in text_lower and text_lower.startswith("<?xml")):
            return "svg"
        
        # JSON always opens with { (object) or [ (array)
        if text_lower.startswith("{") or text_lower.startswith("["):
            return "json"
        
        # CSV needs at least 2 lines (header + data) and commas on all of them
        lines = [l for l in text_lower.split("\n") if l.strip()]
        if len(lines) >= 2 and all("," in l for l in lines[:3]):
            return "csv"

        return "text" # Default — plain prose from the model



    # Pulls the JSON object out of the model output — strips code fences or surrounding prose if needed
    @staticmethod
    def extract_json_payload(output_text):
        # Assign the output text into a clean value with no whitespace
        text = (output_text or "").strip()

        # Try to find JSON inside a code fence first
        if "```" in text:
            for part in text.split("```"):
                candidate = part.strip()
                # Strip language marker (e.g. "json\n{...}") if present
                if "\n" in candidate and not candidate.startswith(("{", "[")):
                    candidate = candidate[candidate.index("\n"):].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    return candidate

        # Fallback: extract outermost { ... } from raw text
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return text[start:end + 1]

        return None
    
    @staticmethod
    def extract_csv_payload(output_text):
        # Assign the output text into a clean value with no whitespace
        text = (output_text or "").strip()

        # The strategy to extract the csv
        if "```" in text:
            for part in text.split("```"):
                candidate = part.strip()
                if candidate.lower().startswith("csv\n"):
                    candidate = candidate[candidate.index("\n"):].strip()
                    
                all_lines = candidate.splitlines()
                lines = []
                for l in all_lines:
                    if l:
                        lines.append(l)
            
                if len(lines) >= 2 and all("," in l for l in lines[:3]):
                    return candidate
        
        return None
                

    # Pulls raw SVG markup out of the model output if the model returned it directly (should rarely be used if ever)
    @staticmethod
    def extract_svg(output_text):
        text = output_text or ""
        lower = text.lower()
        start = lower.find("<svg")
        end = lower.rfind("</svg>")

        if start != -1 and end > start:
            return text[start:end + len("</svg>")]

        return None

    # Parses the model's JSON spec and passes it to the chart renderer to draw the SVG
    # Rather than determining the output, this function creates the output 
    @staticmethod
    def render_svg_from_json(output_text):

        # Use the extract_json_payload function to get the value
        payload = OutputHandler.extract_json_payload(output_text)

        if not payload:
            return None

        try:
            spec = json.loads(payload)

        except Exception:
            return None
        

        if not isinstance(spec, dict):
            return None
        
        return render_chart_svg(spec)
