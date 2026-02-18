import os

from runtime_logic.stage_runtime_logic.prompt_logic import PromptLogic
from runtime_logic.stage_runtime_logic.output_handler import OutputHandler


class StageRunner:

    @staticmethod
    def execute_stage(task_instance_id, artifacts_dir, stage_defs, master_prompt,
                      model_client, model_name, task_stage_instance_service,
                      inputstage_artifact_path, system_prompt=None):

        os.makedirs(artifacts_dir, exist_ok=True)

        # Filter out input stages
        exec_stages = []
        for stage in (stage_defs or []):
            if stage.TaskStageDef_Type.strip().lower() != "input":
                exec_stages.append(stage)

        current_input_path = inputstage_artifact_path
        final_output_path = None
        final_output_type = None

        # Build the system context — primer + master prompt combined into one string for Ollama
        parts = []
        if system_prompt:
            parts.append(system_prompt) # system_prompt holds the primer
        if master_prompt:
            parts.append(master_prompt) # master_prompt holds the agent name, workflow plan, and output rules 
        combined_system = "\n\n".join(parts) # parts array becomes one big string for Ollama to receive

        i = 1 # Start in stage 1
        for stage in exec_stages:
            stage_type = stage.TaskStageDef_Type.strip()
            stage_desc = stage.TaskStageDef_Description.strip()

            # Set the 'stage' variable as running the DB
            stage_instance_id = task_stage_instance_service.create_stage_instance(
                task_instance_id, stage_order=i, stage_name=stage_type,
                status="RUNNING", output_artifact_path=None
            )

            try:
                # Read the output from the previous stage as this stage's input
                with open(current_input_path, "r", encoding="utf-8") as f:
                    input_text = f.read()

                # Build the user-role prompt for this stage
                stage_prompt = PromptLogic.build_stage_prompt(
                    stage_type=stage_type,
                    stage_description=stage_desc,
                    input_text=input_text
                )

                # Check the stage definition to see if JSON output is expected before calling the model
                expected_type = OutputHandler.desired_output_type(stage_type, stage_desc)
                json_mode = expected_type in ("json", "svg") # svg stages also need JSON input for the chart renderer

                # Send the stage prompt to the model — json_mode forces clean JSON output when needed
                output_text = model_client.generate(model_name, stage_prompt, system_prompt=combined_system, json_mode=json_mode)

                if not output_text:
                    raise Exception("Model returned no output.")

                # Use the stage definition type if known, otherwise infer from the actual output
                output_type = expected_type or OutputHandler.infer_output_type(output_text)

                # If SVG expected, try to render from JSON first, then extract raw SVG, else fall back to text
                if output_type == "svg":
                    rendered = OutputHandler.render_svg_from_json(output_text)
                    if rendered:
                        output_text = rendered
                    else:
                        extracted = OutputHandler.extract_svg(output_text)
                        if extracted:
                            output_text = extracted
                        else:
                            output_type = "text"

                # Write the stage output to an artifact file
                extension_dict = {"svg": "svg", "csv": "csv", "json": "json"}

                file_extension = extension_dict.get(output_type, "txt")

                stage_name_clean = stage_type.replace(" ", "_").lower() or "stage"

                artifact_filename = f"{i:02d}_stage_{stage_name_clean}_output.{file_extension}"

                artifact_path = os.path.join(artifacts_dir, artifact_filename)

                with open(artifact_path, "w", encoding="utf-8") as f:
                    f.write(output_text)

                # Write to DB stage is completed
                task_stage_instance_service.mark_stage_completed(stage_instance_id, artifact_path)

                # Pass this output as the input to the next stage (SVG is skpped, can't feed images into the text model)
                if output_type != "svg":
                    current_input_path = artifact_path
                    final_output_path = artifact_path
                    final_output_type = output_type

                elif final_output_path is None:
                    final_output_path = artifact_path
                    final_output_type = output_type

            except Exception as e:
                try:
                    task_stage_instance_service.mark_stage_failed(stage_instance_id, str(e))
                except Exception:
                    pass
                raise

            i += 1 # Move to the next stage number

        return final_output_path, final_output_type # Return the final stage (output)
