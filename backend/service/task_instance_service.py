from backend.dao.task_instance_dao import TaskInstanceDAO
from backend.model.task_instance import TaskInstance


class TaskInstanceService:
    """Service layer for managing TaskInstance runtime execution."""

    def __init__(self):
        self.dao = TaskInstanceDAO()

    # Create a new task instance by using the TaskInstance class and its associated DAO
    def create_task_instance(self, process_id_fk, taskdef_id_fk, status, run_folder):
        """Creates a new TaskInstance entry."""
        new_instance = TaskInstance(
            TaskInstance_ID=None,
            Process_ID_FK=process_id_fk,
            TaskDef_ID_FK=taskdef_id_fk,
            Status=status,
            Run_Folder=run_folder,
            Created_At=None,
            Updated_At=None
        )
        return self.dao.create_task_instance(new_instance)

    # Get the task instance by its ID
    def get_task_instance(self, task_instance_id):
        """Retrieves a TaskInstance by ID."""
        return self.dao.get_task_instance_by_id(task_instance_id)

    # List all the task instances in the table
    def list_task_instances(self):
        """Returns all TaskInstances (newest first)."""
        return self.dao.get_all_task_instances()

    # Update the run folder to the assigned instance path (after run id and folder path has been created and assigned)
    def update_run_folder(self, task_instance_id, run_folder):
        """Updates the on-disk run folder path."""
        return self.dao.update_run_folder(task_instance_id, run_folder)

    # Update the status of the instance whether it succeeds or fails
    def update_status(self, task_instance_id, status):
        """Updates execution status."""
        return self.dao.update_status(task_instance_id, status)

    # Remove a task instance row
    def hard_delete(self, task_instance_id):
        """Hard deletes a TaskInstance row."""
        return self.dao.delete_task_instance(task_instance_id)

    # Delete all task instance rows in the table
    def delete_all(self):
        """Hard deletes all TaskInstance rows (used on startup sweep)."""
        return self.dao.delete_all_task_instances()

    def close(self):
        """Closes the underlying DAO connection."""
        self.dao.close_connection()
