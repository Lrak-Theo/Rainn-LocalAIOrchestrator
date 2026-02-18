 # ==========================================
# File: task_stage_instance_service.py
# Updated in iteration: 4
# Author: Karl Concha
#
# Purpose:
# Service layer for managing TaskStageInstance execution records.
#
# Date: January 2026
# ==========================================

from dao.task_stage_instance_dao import TaskStageInstanceDAO
from model.task_stage_instance import TaskStageInstance


class TaskStageInstanceService:
    """Service layer for managing TaskStageInstance runtime execution."""

    def __init__(self):
        self.dao = TaskStageInstanceDAO()

    def create_stage_instance(self, task_instance_id_fk, stage_order, stage_name, status, output_artifact_path=None):
        """Creates a new TaskStageInstance entry."""
        
        new_stage = TaskStageInstance(
            TaskStageInstance_ID=None,
            TaskInstance_ID_FK=task_instance_id_fk,
            Stage_Order=stage_order,
            Stage_Name=stage_name,
            Status=status,
            Output_Artifact_Path=output_artifact_path,
            Started_At=None,
            Ended_At=None,
            Error_Message=None
        )
        return self.dao.create_stage_instance(new_stage)

    def get_stages_for_task_instance(self, task_instance_id_fk):
        """Retrieves all stage executions for a TaskInstance."""
        return self.dao.get_stages_for_task_instance(task_instance_id_fk)

    def mark_stage_completed(self, stage_instance_id, output_artifact_path):
        """Marks a stage as completed."""
        return self.dao.mark_completed(stage_instance_id, output_artifact_path)

    def mark_stage_failed(self, stage_instance_id, error_message):
        """Marks a stage as failed."""
        return self.dao.mark_failed(stage_instance_id, error_message)

    def clear_outputs_for_task_instance(self, task_instance_id_fk):
        """Clears output paths and error messages for a TaskInstance."""
        return self.dao.clear_outputs_for_task_instance(task_instance_id_fk)

    def delete_for_task_instance(self, task_instance_id_fk):
        """Hard deletes stage instances for a TaskInstance."""
        return self.dao.delete_for_task_instance(task_instance_id_fk)
