from backend.dao.task_stage_instance_dao import TaskStageInstanceDAO
from backend.model.task_stage_instance import TaskStageInstance


class TaskStageInstanceService:
    """Service layer for managing TaskStageInstance runtime execution."""
    
    def __init__(self):
        self.dao = TaskStageInstanceDAO()

    # Create a new task stage instance using the TaskStageInstance class and its DAO
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

    # Retrieve the stages associated with a task instance by using its task instance id FK in the table
    def get_stages_for_task_instance(self, task_instance_id_fk):
        """Retrieves all stage executions for a TaskInstance."""
        return self.dao.get_stages_for_task_instance(task_instance_id_fk)

    # Update the stage status attribute of a stage row to be completed 
    def mark_stage_completed(self, stage_instance_id, output_artifact_path):
        """Marks a stage as completed."""
        return self.dao.mark_completed(stage_instance_id, output_artifact_path)

    # Update the stage status attribute of a stage row to be failed
    def mark_stage_failed(self, stage_instance_id, error_message):
        """Marks a stage as failed."""
        return self.dao.mark_failed(stage_instance_id, error_message)

    # Delete the stages associated 
    def delete_for_task_instance(self, task_instance_id_fk):
        """Hard deletes stage instances for a TaskInstance."""
        return self.dao.delete_for_task_instance(task_instance_id_fk)

    # Delete all task stage instances in the table
    def delete_all(self):
        """ Hard delete all TaskStageInstance rows (used on startup)"""
        return self.dao.delete_all_stage_instances()

    def close(self):
        """Closes the underlying DAO connection."""
        self.dao.close_connection()
