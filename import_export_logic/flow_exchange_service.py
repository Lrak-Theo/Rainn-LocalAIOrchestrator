# ==========================================
# File: flow_exchange_service.py
# Added in iteration: 4
# Author: Karl Concha
#
# Purpose:
# Import/export reusable flow definitions (no run data).
# ==========================================

from datetime import datetime

from service.agent_process_service import AgentProcessService
from service.task_def_service import TaskDefService
from service.task_stage_def_service import TaskStageService


class FlowExchangeService:
    """Service for exporting and importing Rainn flow definitions."""

    SCHEMA_VERSION = "rainn.flow.v1"

    def __init__(self):
        self.process_service = AgentProcessService()
        self.taskdef_service = TaskDefService()
        self.stage_service = TaskStageService()

    def export_flow(self, process_id):
        process = self.process_service.get_process(process_id)
        if not process:
            return None

        taskdef = self.taskdef_service.get_taskdef_by_id(process.Operation_Selected)
        if not taskdef:
            return None

        stages = self.stage_service.get_stages_for_task(taskdef.TaskDef_ID)
        stages_sorted = sorted(stages, key=lambda s: s.TaskStageDef_ID)

        flow = {
            "agent_name": process.Agent_Name,
            "ai_model": process.AI_Model,
            "task_title": taskdef.TaskDef_Name,
            "task_description": taskdef.TaskDef_Description,
            "primer_text": process.Agent_Priming or "",
            "stages": [
                {
                    "order": idx + 1,
                    "name": s.TaskStageDef_Type,
                    "description": s.TaskStageDef_Description
                }
                for idx, s in enumerate(stages_sorted)
                if (s.TaskStageDef_Type or "").strip().lower() != "input"
            ]
        }

        return {
            "schema_version": self.SCHEMA_VERSION,
            "exported_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "flow": flow,
            "source": "rainn"
        }

    def validate_flow_payload(self, payload):
        if not isinstance(payload, dict):
            return False, "Invalid JSON format."
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            return False, "Unsupported schema_version."
        flow = payload.get("flow")
        if not isinstance(flow, dict):
            return False, "Missing flow definition."
        required = ["agent_name", "ai_model", "task_title", "task_description", "stages"]
        for key in required:
            if key not in flow or flow[key] in (None, ""):
                return False, f"Missing required field: flow.{key}"
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

        taskdefs = self.taskdef_service.list_taskdefs()
        existing_task_names = {t.TaskDef_Name for t in taskdefs}

        processes = self.process_service.list_processes()
        existing_agent_names = {p.Agent_Name for p in processes}

        task_title = self._unique_name(flow["task_title"], existing_task_names)
        agent_name = self._unique_name(flow["agent_name"], existing_agent_names)

        taskdef_id = self.taskdef_service.create_taskdef(
            task_title,
            flow.get("task_description") or ""
        )

        stages = sorted(flow["stages"], key=lambda s: s.get("order", 0))
        has_output = any((s.get("name") or "").strip().lower() == "output" for s in stages)
        for s in stages:
            stage_name = (s.get("name") or "").strip()
            stage_desc = (s.get("description") or "").strip()
            if stage_name.lower() == "input":
                continue
            if stage_name and stage_desc:
                self.stage_service.create_stage(taskdef_id, stage_name, stage_desc)

        if not has_output:
            self.stage_service.create_stage(
                taskdef_id,
                "output",
                "Present the final response for the user."
            )

        created = self.process_service.create_process(
            user_id=user_id,
            agent_name=agent_name,
            agent_priming=flow.get("primer_text") or "",
            taskdef_id=taskdef_id,
            ai_model=flow.get("ai_model") or ""
        )
        return getattr(created, "Process_ID", created)

    @staticmethod
    def _unique_name(base_name, existing_names):
        base_name = (base_name or "").strip() or "Imported Flow"
        candidate = f"{base_name} (Imported)" if base_name in existing_names else base_name
        if candidate not in existing_names:
            return candidate
        suffix = 1
        while f"{candidate} ({suffix})" in existing_names:
            suffix += 1
        return f"{candidate} ({suffix})"
