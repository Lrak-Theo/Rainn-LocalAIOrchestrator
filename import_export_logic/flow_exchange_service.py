from datetime import datetime

from backend.service.agent_process_service import AgentProcessService
from backend.service.task_def_service import TaskDefService
from backend.service.task_stage_def_service import TaskStageService


class FlowExchangeService:
    """Service for exporting and importing Rainn flow definitions."""

    SCHEMA_VERSION = "rainn.flow.v1"  # Version tag embedded in every exported payload

    def __init__(self):
        self.process_service = AgentProcessService()
        self.taskdef_service = TaskDefService()
        self.stage_service = TaskStageService()

    def export_flow(self, process_id):
        # Fetch the process and its linked taskdef — return None if either is missing
        process = self.process_service.get_process(process_id)
        if not process:
            return None

        taskdef = self.taskdef_service.get_taskdef_by_id(process.Operation_Selected)
        if not taskdef:
            return None

        # Sort stages by ID to preserve their original creation order
        stages = self.stage_service.get_stages_for_task(taskdef.TaskDef_ID)
        stages_sorted = sorted(stages, key=lambda s: s.TaskStageDef_ID)

        # Build the stages list in creation order
        stage_list = []
        order = 1
        for s in stages_sorted:
            stage_list.append({
                "order": order,
                "name": s.TaskStageDef_Type,
                "description": s.TaskStageDef_Description
            })
            order += 1

        # Build the flow dict from the process and taskdef records
        flow = {
            "agent_name": process.Agent_Name,
            "ai_model": process.AI_Model,
            "task_title": taskdef.TaskDef_Name,
            "task_description": taskdef.TaskDef_Description,
            "primer_text": process.Agent_Priming or "",
            "stages": stage_list
        }

        # Wrap the flow in the versioned export envelope
        return {
            "schema_version": self.SCHEMA_VERSION,
            "exported_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "flow": flow,
            "source": "rainn"
        }

    def validate_flow_payload(self, payload):
        # Top-level must be a dict
        if not isinstance(payload, dict):
            return False, "Invalid JSON format."
        
        # Reject payloads from incompatible schema versions
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            return False, "Unsupported schema_version."
        flow = payload.get("flow")
        if not isinstance(flow, dict):
            return False, "Missing flow definition."
        
        # Check all required fields are present and non-empty
        required = ["agent_name", "ai_model", "task_title", "task_description", "stages"]
        for key in required:
            if key not in flow or flow[key] in (None, ""):
                return False, f"Missing required field: flow.{key}"
            
        # Stages must be a non-empty list of objects with name and description
        stages = flow.get("stages")
        if not isinstance(stages, list) or not stages:
            return False, "Stages must be a non-empty array."
        for s in stages:
            if not isinstance(s, dict):
                return False, "Each stage must be an object."
            if not s.get("name") or not s.get("description"):
                return False, "Each stage must include name and description."
        return True, ""

    def import_flow(self, payload, user_id=1):
        flow = payload["flow"]

        # Collect existing names into plain lists to check for duplicates
        existing_task_names = []
        for t in self.taskdef_service.list_taskdefs():
            existing_task_names.append(t.TaskDef_Name)

        existing_agent_names = []
        for p in self.process_service.list_processes():
            existing_agent_names.append(p.Agent_Name)

        # Deduplicate names before writing to the DB
        task_title = self._unique_name(flow["task_title"], existing_task_names)
        agent_name = self._unique_name(flow["agent_name"], existing_agent_names)

        # Create the taskdef first — stages are linked to it by ID
        taskdef_id = self.taskdef_service.create_taskdef(
            task_title,
            flow.get("task_description") or ""
        )

        # Sort stages by their order field before inserting
        stages = sorted(flow["stages"], key=lambda s: s.get("order", 0))

        # Persist stages exactly in their creation order from the payload.
        has_output = False

        for s in stages:
            stage_name = (s.get("name") or "").strip()
            stage_desc = (s.get("description") or "").strip()
            stage_name_l = stage_name.lower()

            if stage_name_l == "output":
                has_output = True

            if stage_name and stage_desc:
                self.stage_service.create_stage(taskdef_id, stage_name, stage_desc)

        # If the exported flow had no output stage, add a default one / Soon to be redunant for UI error improvements and constraints
        if not has_output:
            self.stage_service.create_stage(
                taskdef_id,
                "output",
                "Present the final response for the user."
            )

        # Create the agent process record tied to the new taskdef
        created = self.process_service.create_process(
            user_id=user_id,
            agent_name=agent_name,
            agent_priming=flow.get("primer_text"),
            taskdef_id=taskdef_id,
            ai_model=flow.get("ai_model")
            ) 

        # Return the new process ID — handle both object and raw int return from service
        if hasattr(created, "Process_ID"):
            return created.Process_ID
        return created

    @staticmethod
    def _unique_name(base_name, existing_names):
        if not base_name:
            base_name = "Imported Flow"
        base_name = base_name.strip()

        # Append "(Imported)" if the name already exists
        if base_name in existing_names:
            new_name = base_name + " (Imported)"
        else:
            new_name = base_name

        if new_name not in existing_names:
            return new_name

        # If still clashing, keep incrementing the suffix until unique
        suffix = 1
        while f"{new_name} ({suffix})" in existing_names:
            suffix += 1
        return f"{new_name} ({suffix})"
