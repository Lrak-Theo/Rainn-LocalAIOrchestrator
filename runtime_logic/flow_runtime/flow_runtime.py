
# Agent runtime is the orchestration logic

# Importing all needed files
import os 

from runtime_logic.input_stage_logic.input_normaliser import InputNormaliser
from runtime_logic.stage_runtime_logic.run_stage import StageRunner
from runtime_logic.stage_runtime_logic.prompt_logic import PromptLogic

from service.task_instance_service import TaskInstanceService
from service.task_stage_instance_service import TaskStageInstanceService
from service.agent_process_service import AgentProcessService
from service.task_def_service import TaskDefService
from service.task_stage_def_service import TaskStageService

from integrations.model_client_ollama import OllamaModelClient

class FlowRuntime:
    """ Orchestrates a full agent flow from uploaded file --> stage output """

    @staticmethod
    def run_flow(process_id, taskdef_id, file_path): 
        
        task_instance_service = TaskInstanceService()
        stage_instance_service = TaskStageInstanceService()

        agent_process_service = AgentProcessService()
        task_def_service = TaskDefService()
        stage_service = TaskStageService()

        
        run_id = None # Pre-declared so the except block can safely reference it if creation fails
        input_stage_id = None # Pre-declared so the except block can mark Stage 0 as FAILED if an error occurs

        try:
            # Step 1: Creating a run record in the DB --> return the auto-assigned run_ID
            run_id = task_instance_service.create_task_instance(process_id, taskdef_id, "RUNNING", "")

            # Step 2: Creating the run folder and updating the run_id with its path
            run_folder = os.path.join("agent_runs", str(run_id))
            os.makedirs(run_folder, exist_ok=True) # Won't crash if the folder already exits
            task_instance_service.update_run_folder(run_id, run_folder)

            # Step 3: Creating the Stage 0 (input stage) record in the DB
            input_stage_id = stage_instance_service.create_stage_instance(run_id, stage_order=0, stage_name="input", status="RUNNING", output_artifact_path=None)

            # Step 4: Normalise uploaded file(s) to plain text (purpose of Stage 0)
            normalised_text, stage0_artifact_path = InputNormaliser.run_multi(files=file_path, run_folder=run_folder)

            stage_instance_service.mark_stage_completed(input_stage_id, stage0_artifact_path) #marking stage 0 completed while storing th artifact path

            # Step 5: Fetch the selected flow from the DB
            selected_flow = agent_process_service.get_process(process_id) # Get the selected process ID using service
            selected_taskdef = task_def_service.get_taskdef_by_id(taskdef_id) # Get the selected taskdef ID using service 
            selected_stage_defs = stage_service.get_stages_for_task(taskdef_id) # Get the selected stages ID using service

            primer = selected_flow.Agent_Priming
            model_name = selected_flow.AI_Model

            # Step 6: Compiling the Master Prompt
            master_prompt = PromptLogic.compile_master_prompt(selected_taskdef, selected_stage_defs)

            # Step 7: Executing the stages 1..N in sequence
            final_output_path, final_output_type = StageRunner.execute_stage(
                task_instance_id=run_id,
                artifacts_dir=os.path.join(run_folder, "artifacts"),
                stage_defs=selected_stage_defs,
                master_prompt=master_prompt,
                model_client=OllamaModelClient(),
                model_name=model_name,
                task_stage_instance_service=stage_instance_service,
                inputstage_artifact_path=stage0_artifact_path,
                system_prompt=primer
            )

            # Step 8: Read final output and marking run as COMPLETED
            with open(final_output_path, "r", encoding="utf-8") as f:
                output_text = f.read()
            output_type = final_output_type

            task_instance_service.update_status(run_id, "COMPLETED")

            return {
                "task_instance_id": run_id,
                "output_text": output_text,
                "output_type": output_type,
                "output_artifact_path": final_output_path
            } # Return as dict in order for app.py to unpack and read the results
        
        except Exception as e:
            if input_stage_id:
                stage_instance_service.mark_stage_failed(input_stage_id, str(e))

            if run_id:
                task_instance_service.update_status(run_id, "FAILED")
                
            return {
                "task_instance_id": run_id,
                "output_text": f"Error: {e}",
                "output_type": "text",
                "output_artifact_path": None
            }