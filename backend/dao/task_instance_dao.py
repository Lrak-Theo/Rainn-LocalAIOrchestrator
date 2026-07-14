import sqlite3
from backend.model.task_instance import TaskInstance


class TaskInstanceDAO:

    def __init__(self, db_name="rainn.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def _row_to_instance(self, row):
        return TaskInstance(
            row["TaskInstance_ID"],
            row["Process_ID_FK"],
            row["TaskDef_ID_FK"],
            row["Status"],
            row["Run_Folder"],
            row["Created_At"],
            row["Updated_At"]
        )
    
    # Create a Task instance #########################################################
    def create_task_instance(self, task_instance: TaskInstance): # Create a task instance row
        """Creates a new TaskInstance row and returns its ID."""
        self.cursor.execute(
            """
            INSERT INTO TaskInstance
                (Process_ID_FK, TaskDef_ID_FK, Status, Run_Folder)
            VALUES (?, ?, ?, ?)
            """,
            (
                task_instance.Process_ID_FK,
                task_instance.TaskDef_ID_FK,
                task_instance.Status,
                task_instance.Run_Folder,
            )
        )
        self.connection.commit()
        return self.cursor.lastrowid
    #########################################################

    # Fetch a Task instance #########################################################
    def get_task_instance_by_id(self, task_instance_id): # Fetch a task instance by using its ID 
        """Fetches a TaskInstance by primary key."""
        self.cursor.execute(
            "SELECT * FROM TaskInstance WHERE TaskInstance_ID = ?",
            (task_instance_id,)
        )
        row = self.cursor.fetchone()
        return self._row_to_instance(row) if row else None
    

    def get_all_task_instances(self): # Fetch all task instances in the table
        """Returns all TaskInstances (newest first)."""
        self.cursor.execute(
            "SELECT * FROM TaskInstance ORDER BY TaskInstance_ID DESC"
        )
        return [self._row_to_instance(row) for row in self.cursor.fetchall()]
    #########################################################

    # Update a Task instance #########################################################
    def update_status(self, task_instance_id, status): # Update the status column of the task instance row (for granular updates)
        """Updates execution status and timestamp."""
        self.cursor.execute(
            """
            UPDATE TaskInstance
            SET Status = ?, Updated_At = CURRENT_TIMESTAMP
            WHERE TaskInstance_ID = ?
            """,
            (status, task_instance_id)
        )
        self.connection.commit()

    def update_run_folder(self, task_instance_id, run_folder): 
    # The task instance created declares the folder path empty, update_run_folder gets called when run_id gets assigned and agent_runs/<run_id> gets assigned
        """Persists the filesystem run folder path."""
        self.cursor.execute(
            """
            UPDATE TaskInstance
            SET Run_Folder = ?, Updated_At = CURRENT_TIMESTAMP
            WHERE TaskInstance_ID = ?
            """,
            (run_folder, task_instance_id)
        )
        self.connection.commit()
    #########################################################

    # Delete a Task instance #########################################################
    def delete_task_instance(self, task_instance_id): # Delete a task instance row in the table
        """Hard deletes a TaskInstance row."""
        self.cursor.execute(
            "DELETE FROM TaskInstance WHERE TaskInstance_ID = ?",
            (task_instance_id,)
        )
        self.connection.commit()

    def delete_all_task_instances(self): # Delete all task instances in the table (for minimal data retention)
        """Hard deletes all TaskInstance rows."""
        self.cursor.execute("DELETE FROM TaskInstance")
        self.connection.commit()
    #########################################################


    def close_connection(self):
        self.connection.close()
