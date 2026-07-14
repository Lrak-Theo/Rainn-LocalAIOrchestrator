import sqlite3
from backend.model.task_stage_instance import TaskStageInstance


class TaskStageInstanceDAO:

    def __init__(self, db_name="rainn.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    # Create a stage instance  #############################
    def create_stage_instance(self, stage_instance: TaskStageInstance): # Create a stage instance row and return the ID for traceback
        """Creates a TaskStageInstance row and returns its ID."""
        self.cursor.execute(
            """
            INSERT INTO TaskStageInstance
                (TaskInstance_ID_FK, Stage_Order, Stage_Name,
                 Status, Output_Artifact_Path, Started_At)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                stage_instance.TaskInstance_ID_FK,
                stage_instance.Stage_Order,
                stage_instance.Stage_Name,
                stage_instance.Status,
                stage_instance.Output_Artifact_Path
            )
        )
        self.connection.commit()
        return self.cursor.lastrowid
    ##########################################################

    # Update a stage instance  #############################
    # The stage instances updates are only if stage running is successful or unsucesseful
    def mark_completed(self, stage_instance_id, output_artifact_path): # Update stage status as completed
        """Marks a stage as completed and records its output artifact."""
        self.cursor.execute(
            """
            UPDATE TaskStageInstance
            SET Status = 'COMPLETED',
                Output_Artifact_Path = ?,
                Ended_At = CURRENT_TIMESTAMP
            WHERE TaskStageInstance_ID = ?
            """,
            (output_artifact_path, stage_instance_id)
        )
        self.connection.commit()

    def mark_failed(self, stage_instance_id, error_message): # Update stage status as failed
        """Marks a stage as failed and stores the error message."""
        self.cursor.execute(
            """
            UPDATE TaskStageInstance
            SET Status = 'FAILED',
                Error_Message = ?,
                Ended_At = CURRENT_TIMESTAMP
            WHERE TaskStageInstance_ID = ?
            """,
            (error_message, stage_instance_id)
        )
        self.connection.commit()
    ##########################################################

    # Retreive task stage instances  #############################
    def get_stages_for_task_instance(self, task_instance_id_fk): # Fetch the stages for a task instance 
        """Returns all stage executions for a TaskInstance."""
        self.cursor.execute(
            """
            SELECT * FROM TaskStageInstance
            WHERE TaskInstance_ID_FK = ?
            ORDER BY Stage_Order ASC
            """,
            (task_instance_id_fk,)
        )
        rows = self.cursor.fetchall()

        return [
            TaskStageInstance(
                r["TaskStageInstance_ID"],
                r["TaskInstance_ID_FK"],
                r["Stage_Order"],
                r["Stage_Name"],
                r["Status"],
                r["Output_Artifact_Path"],
                r["Started_At"],
                r["Ended_At"],
                r["Error_Message"]
            )
            for r in rows
        ]

    def get_all_stage_instances(self): # Fetch all stage instances in the table
        """Returns all TaskStageInstances (newest first)."""
        self.cursor.execute(
            "SELECT * FROM TaskStageInstance ORDER BY TaskStageInstance_ID DESC"
        )
        rows = self.cursor.fetchall()

        return [
            TaskStageInstance(
                row["TaskStageInstance_ID"],
                row["TaskInstance_ID_FK"],
                row["Stage_Order"],
                row["Stage_Name"],
                row["Status"],
                row["Output_Artifact_Path"],
                row["Started_At"],
                row["Ended_At"],
                row["Error_Message"]
            )
            for row in rows
        ]
    ##########################################################

    # Delete task stage instances  #############################
    def delete_for_task_instance(self, task_instance_id_fk): # Delete the stage instances related to the task instance 
        """Hard deletes TaskStageInstance rows for a TaskInstance."""
        self.cursor.execute(
            "DELETE FROM TaskStageInstance WHERE TaskInstance_ID_FK = ?",
            (task_instance_id_fk,)
        )
        self.connection.commit()

    def delete_all_stage_instances(self): # For full wipe of all stage instances before system startup
        """ Hard deletes all TaskStageInstance rows. """
        self.cursor.execute("DELETE FROM TaskStageInstance")
        self.connection.commit()
    ##########################################################

    def close_connection(self):
        self.connection.close()
