class PromptLogic:

    @staticmethod
    # Function to create a workflow prompt to be given to the AI model
    def compile_master_prompt(taskdef, stage_defs): 

        # Create a plain lines list
        plain_lines = []

        # i == stage... begin from stage 1
        i = 1

        # looping the stage in stage_defs
        for stage in stage_defs:
            stage_type = stage.TaskStageDef_Type.strip()
            stage_desc = stage.TaskStageDef_Description.strip()

            if stage_desc:
                # Append the stage desc to stage type with ' - ' 
                stage_type += f" - {stage_desc}" 

            # Populate the list with the stage type and description turned into string
            plain_lines.append(f"{i}. {stage_type}") 

            # Next stage...
            i += 1

        # Create a concatenated string of plain_lines
        stage_plan = "\n".join(plain_lines) 

        agent_name = taskdef.TaskDef_Name.strip()

        # Return the full prompt structure workflow as f string
        return f"""
    [AGENT TEMPLATE]
    Name: {agent_name}

    [WORKFLOW PLAN]
    {stage_plan}

    [OUTPUT RULES]
    - Complete one stage at a time.
    - Keep outputs clear and structured.
    - Do not invent facts not present in the input.
    """.strip()



    @staticmethod
    # To determine what output rules will be given based on the output type
    def output_rules_for_stage(stage_type, stage_description):
        stage_type_l = stage_type.lower()

        # Concatenate the two attributes into one single string 
        haystack = f"{stage_type_l} {stage_description.lower()}" 

        # if stage type is an output... use this instruction
        if stage_type_l == "output":
            return """
    [OUTPUT RULES FOR FINAL STAGE]
    - This is the final stage. Do not mention stages, pipelines, or scripts.
    - Do not ask to proceed or request confirmation.
    - Provide the final response only.
    - Do not include code, pseudocode, or implementation steps.
    """.strip()

        # if the haystack string contains any of the given words below... use this instruction
        if any(w in haystack for w in ["graph", "visual", "chart", "diagram", "visualize", "plot", "infographic"]):
            return """
    [OUTPUT RULES FOR GRAPH]
    - Return ONLY JSON with keys: title, labels, values, x_label, y_label.
    - "labels" must be a list of strings and "values" must be a list of numbers.
    - Do not include prose, markdown, or code fences.
    """.strip()

        # if the keywords relating to tables or spreadhseets is in the haystack word ... use this instruction
        if "csv" in haystack or "table" in haystack or "format" in haystack:
            return """
    [OUTPUT RULES FOR TABLE]
    - Return ONLY raw CSV. No prose, no introduction, no explanation, no markdown, no code fences.
    - Your response must begin immediately with the header row on line 1. No sentences before it.
    - Do not write anything after the last data row.
    """.strip()

        # if the keywords relating to json is in the haystack word ... use this instruction
        if "json" in haystack or "structured" in haystack:
            return """
    [OUTPUT RULES FOR STRUCTURED]
    - Return ONLY valid JSON.
    - Do not wrap in code fences or add commentary.
    """.strip()

        # else return no instruction
        return ""
    


    @staticmethod
    # The stage-by-stage prompts
    def build_stage_prompt(stage_type, stage_description, input_text):

        # Get the output rules from the function determingin the output rules
        output_rules = PromptLogic.output_rules_for_stage(stage_type, stage_description)

        # Add a priority instruction
        priority_rules = """
    [PRIORITY RULES]
    - The system primer sets global rules, tone, and formatting.
    - Stage instructions define the task for this step.
    - If there is a conflict, follow the system primer.
    """.strip()

        # Return the final stage prompt (different from the master prompt building)
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