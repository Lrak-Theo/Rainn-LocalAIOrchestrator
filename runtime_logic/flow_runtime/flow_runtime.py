# Importing all needed files
import os 

from runtime_logic.stage_runtime_logic.run_stage import StageRunner
from runtime_logic.stage_runtime_logic.stage_prompt_logic import PromptLogic

from integrations.model_client_ollama import OllamaModelClient

class FlowRuntime:
    """ Orchestrates a full agent flow from uploaded file --> stage output """
    
    def __init__(self, task_instance_service, stage_instance_service, agent_process_service, task_def_service, task_stage_service):
        self.task_instance_service_import = task_instance_service
        self.stage_instance_service_import = stage_instance_service
        self.agent_process_service_import = agent_process_service
        self.task_def_service_import = task_def_service
        self.task_stage_service_import = task_stage_service


    def run_flow(self,process_id, taskdef_id, file_path, socketio): 
        print(f"run_flow started for process {process_id}")

        task_instance_service = self.task_instance_service_import()
        stage_instance_service = self.stage_instance_service_import()
        agent_process_service = self.agent_process_service_import()
        task_def_service = self.task_def_service_import()
        task_stage_service = self.task_stage_service_import()

        
        run_id = None # Pre-declared so the except block can safely reference it if creation fails

        try:
            # Step 1: Creating a run record in the DB --> return the auto-assigned run_ID
            run_id = task_instance_service.create_task_instance(process_id, taskdef_id, "RUNNING", "")

            # Step 2: Creating the run folder and updating the run_id with its path
            run_folder = os.path.join("agent_runs", str(run_id))
            os.makedirs(run_folder, exist_ok=True) # Won't crash if the folder already exits
            task_instance_service.update_run_folder(run_id, run_folder)
           
            # Step 5: Fetch the selected flow from the DB
            selected_flow = agent_process_service.get_process(process_id) # Get the selected process ID using service
            selected_taskdef = task_def_service.get_taskdef_by_id(taskdef_id) # Get the selected taskdef ID using service 
            selected_stage_defs = task_stage_service.get_stages_for_task(taskdef_id) # Get the selected stages ID using service

            primer = selected_flow.Agent_Priming
            model_name = selected_flow.AI_Model

            # Step 6: Compiling the Master Prompt (CALLING THE PROMPTLOGIC CLASS HERE)
            master_prompt = PromptLogic.compile_master_prompt(selected_taskdef, selected_stage_defs)

            # Step 7: Executing the stages 1..N in sequence (CALLING THE STAGE RUNNER CLASS HERE)
            final_output_path, final_output_type = StageRunner.execute_stage(
                task_instance_id=run_id,
                artifacts_dir=os.path.join(run_folder, "artifacts"),
                stage_defs=selected_stage_defs,
                master_prompt=master_prompt,
                model_client=OllamaModelClient(), # CALLING THE OLLAMA MODEL CLIENT CALSS HERE 
                model_name=model_name,
                task_stage_instance_service=stage_instance_service,
                input_files=file_path,
                socketio=socketio, # From the app.py import
                system_prompt=primer
            )

            # Step 8: Read final output and marking run as COMPLETED
            with open(final_output_path, "r", encoding="utf-8") as f:
                output_text = f.read()
            output_type = final_output_type

            task_instance_service.update_status(run_id, "COMPLETED")

            # SocketIO emit pattern adapted from: https://www.youtube.com/watch?v=bUfUKtJqaxQ — I added output_text and output_type to the payload.
            socketio.emit("run complete", {
                "output_text": output_text,
                "output_type": output_type,
                "output_filename": os.path.basename(final_output_path)
            }) # Notifying the websocket that the stage n is complete

            return {
                "task_instance_id": run_id,
                "output_text": output_text,
                "output_type": output_type,
                "output_artifact_path": final_output_path
            } # Return as dict in order for app.py to unpack and read the results
        
        except Exception as e:
            if run_id:
                task_instance_service.update_status(run_id, "FAILED")
            
            socketio.emit("run complete", {
                "output_text": f"Error: {e}",
                "output_type": "text"
            })

            return {
                "task_instance_id": run_id,
                "output_text": f"Error: {e}",
                "output_type": "text",
                "output_artifact_path": None
            }
        
        finally:

            # Delete the uploaded temp files when run succeeds or fails
            for file in (file_path):
                if os.path.exists(file["path"]):
                    os.remove(file["path"])


            task_instance_service.close()
            stage_instance_service.close()
            agent_process_service.close()
            task_def_service.close()
            task_stage_service.close()