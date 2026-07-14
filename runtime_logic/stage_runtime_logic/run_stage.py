import os

from runtime_logic.stage_runtime_logic.stage_prompt_logic import PromptLogic
from runtime_logic.stage_runtime_logic.stage_output_handler import OutputHandler
from runtime_logic.input_stage_logic.input_normaliser import InputNormaliser


class StageRunner:

    @staticmethod
    # Execute the stages
    def execute_stage(task_instance_id, artifacts_dir, stage_defs, master_prompt,
                      model_client, model_name, task_stage_instance_service,
                      input_files, socketio, system_prompt=None):

        # First create the directory
        os.makedirs(artifacts_dir, exist_ok=True)

        # Create a baseline normalised input artifact so flows can run even when
        # the first explicit stage is not "input".
        initial_input_path = InputNormaliser.run_multi(
            files=input_files,
            artifacts_directory=artifacts_dir,
            stage_index=0
        )

        # Assign the variables to be None first
        current_input_path = initial_input_path
        final_output_path = None
        final_output_type = None

        # Get the length of the stages for count of progress bar
        total_stages = len(stage_defs)

        i = 1 # Start count / stage from 1 

        # Build the system context — primer + master prompt combined into one string for Ollama
        parts = []

        # system_prompt holds the primer
        if system_prompt:
            parts.append(system_prompt) 

        # master_prompt holds the agent name, workflow plan, and output rules 
        if master_prompt:
            parts.append(master_prompt)

        # parts array becomes one big string for Ollama to receive
        combined_system = "\n\n".join(parts) 

        # Looping the stage_defs
        for stage in stage_defs:
            stage_type = stage.TaskStageDef_Type.strip()
            stage_desc = stage.TaskStageDef_Description.strip()

            # Set the output type to be txt in the beginning
            output_type = "txt"

            stage_name_clean = stage_type.replace(" ", "_").lower() or "stage"
            artifact_filename = f"{i:02d}_stage_{stage_name_clean}_output.txt"            

            # Set the 'stage' variable as running the DB
            stage_instance_id = task_stage_instance_service.create_stage_instance(
                task_instance_id, stage_order=i, stage_name=stage_type,
                status="RUNNING", output_artifact_path=None
            )

            try:
                # Input stage 
                if stage_type.lower() == "input":

                    # USING THE INPUTNORMALISER CLASS HERE
                    artifact_path = InputNormaliser.run_multi(files=input_files, artifacts_directory=artifacts_dir, stage_index=i)

                    # Setting the artifact path to be named current_input_path for clearer naming
                    current_input_path = artifact_path 

                # Free text stage
                else:
                    if not current_input_path:
                        raise Exception("No input artifact available for this stage.")

                    # Read the output from the previous stage as this stage's input
                    with open(current_input_path, "r", encoding="utf-8") as f:
                        input_text = f.read()

                    # Build the user-role prompt for this stage (USING THE PROMPTLOGIC CLASS HERE)
                    stage_prompt = PromptLogic.build_stage_prompt(
                        stage_type=stage_type,
                        stage_description=stage_desc,
                        input_text=input_text
                    )

                    # Check the stage definition to see if JSON output is expected before calling the model
                    expected_type = OutputHandler.desired_output_type(stage_type, stage_desc)
                    json_mode = expected_type in ("json", "svg") # svg stages also need JSON input for the chart renderer

                    # Send the stage prompt to the model — json_mode forces clean JSON output when needed (This is the ollama class)
                    output_text = model_client.generate(model_name, stage_prompt, system_prompt=combined_system, json_mode=json_mode)

                    if not output_text:
                        raise Exception("Model returned no output.")


                    # OUTPUT HANDLER CLASSES USED HERE

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

                    elif output_type == "csv":
                        extracted = OutputHandler.extract_csv_payload(output_text)
                        if extracted:
                            output_text = extracted

                    # # 

                    # Write the stage output to an artifact file
                    extension_dict = {"svg": "svg", "csv": "csv", "json": "json"}

                    file_extension = extension_dict.get(output_type, "txt")

                    artifact_filename = f"{i:02d}_stage_{stage_name_clean}_output.{file_extension}"

                    artifact_path = os.path.join(artifacts_dir, artifact_filename)

                    with open(artifact_path, "w", encoding="utf-8") as f:
                        f.write(output_text)

                    # Pass this output as the input to the next stage (SVG is skpped, can't feed images into the text model)
                    if output_type != "svg":
                        current_input_path = artifact_path


                # Write to DB that stage is completed
                task_stage_instance_service.mark_stage_completed(stage_instance_id, artifact_path)

                # Creating the stage context by reading the artifact output
                stage_context = None
                if output_type != "svg" and artifact_path and os.path.exists(artifact_path):
                    with open(artifact_path, "r", encoding="utf-8") as f:
                        stage_text = f.read().strip()
                    if stage_text:
                        stage_context = {
                            "stage_number": i,
                            "stage_type": stage_type,
                            "output_type": output_type,
                            "content": stage_text
                        } # stage_context var becomes a dictionary to be passed 

                # SocketIO emit pattern adapted from: https://www.youtube.com/watch?v=bUfUKtJqaxQ — I added percentage calculation based on current stage index vs total stages.
                # SocketIO progress bar integration
                progress_bar_percent = int((i / total_stages) * 100) # Determining current stage number
                socketio.emit("update progress", {
                    "percent": progress_bar_percent,
                    "stage_number": i,
                    "stage_name": stage_name_clean,
                    "filename": artifact_filename, # Passing on the file name to the JS script for artifact downloads
                    "run_id": task_instance_id, # Passing on the run id to the JS script for artifact downloads
                    "stage_context": stage_context # Stage context array is also passed to enable flow context addition
                }) # This line of code is responsible for marking the stage complete visually and show status


                # Recording the last stage as final output
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
