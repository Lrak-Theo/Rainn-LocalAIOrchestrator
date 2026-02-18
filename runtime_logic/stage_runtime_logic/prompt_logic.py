class PromptLogic:

    @staticmethod
    def compile_master_prompt(taskdef, stage_defs):
        plain_lines = []
        i = 1
        for stage in stage_defs:
            stage_type = stage.TaskStageDef_Type.strip()
            stage_desc = stage.TaskStageDef_Description.strip()

            parts = [x for x in [stage_type, stage_desc] if x]
            plain_lines.append(f"{i}. {' - '.join(parts)}")
            i += 1
        
        stage_plan = "\n".join(plain_lines)
        agent_name = taskdef.TaskDef_Name.strip()
        agent_desc = taskdef.TaskDef_Description.strip()

        return f"""
    [AGENT TEMPLATE]
    Name: {agent_name}
    Description: {agent_desc}

    [WORKFLOW PLAN]
    {stage_plan}

    [OUTPUT RULES]
    - Complete one stage at a time.
    - Keep outputs clear and structured.
    - Do not invent facts not present in the input.
    """.strip()

    @staticmethod
    def output_rules_for_stage(stage_type, stage_description):
        stage_type_l = stage_type.lower()
        haystack = f"{stage_type_l} {stage_description.lower()}"

        if stage_type_l == "output":
            return """
    [OUTPUT RULES FOR FINAL STAGE]
    - This is the final stage. Do not mention stages, pipelines, or scripts.
    - Do not ask to proceed or request confirmation.
    - Provide the final response only.
    - Do not include code, pseudocode, or implementation steps.
    """.strip()

        if any(w in haystack for w in ["graph", "visual", "chart", "diagram", "visualize", "plot", "infographic"]):
            return """
    [OUTPUT RULES FOR GRAPH]
    - Return ONLY JSON with keys: title, labels, values, x_label, y_label.
    - "labels" must be a list of strings and "values" must be a list of numbers.
    - Do not include prose, markdown, or code fences.
    """.strip()

        if "csv" in haystack or "table" in haystack:
            return """
    [OUTPUT RULES FOR TABLE]
    - Return ONLY CSV text (no prose, no markdown).
    - First line must be the header row.
    """.strip()

        if "json" in haystack or "structured" in haystack:
            return """
    [OUTPUT RULES FOR STRUCTURED]
    - Return ONLY valid JSON.
    - Do not wrap in code fences or add commentary.
    """.strip()

        return ""
    
    @staticmethod
    def build_stage_prompt(stage_type, stage_description, input_text):
        output_rules = PromptLogic.output_rules_for_stage(stage_type, stage_description)

        priority_rules = """
    [PRIORITY RULES]
    - The system primer sets global rules, tone, and formatting.
    - Stage instructions define the task for this step.
    - If there is a conflict, follow the system primer.
    """.strip()

        return f"""
    [CURRENT STAGE]
    Type: {stage_type}
    Goal: {stage_description}

    [CURRENT INPUT]
    {input_text}

    [PRIORITY]
    {priority_rules}

    [INSTRUCTIONS]
    Perform ONLY this stage. Output must be suitable as input to the next stage.
    {output_rules}
    """.strip()