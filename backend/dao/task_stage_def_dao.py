import sqlite3
from backend.model.task_stage_def import TaskStageDef


class TaskStageDefDAO:

    def __init__(self, db_name="rainn.db"):
        """ Initializes the connection to the SQLite database. """

        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    # Add Task Stage Def #############################
    def add_TaskStageDef(self, stage_def): 
        """ Inserts a new TaskStageDef record into the database. """

        self.cursor.execute(
            '''INSERT INTO TaskStageDef (
                TaskDef_ID_FK, TaskStageDef_Type, TaskStageDef_Description)
               VALUES (?, ?, ?)''',
            (stage_def.TaskDef_ID_FK,
             stage_def.TaskStageDef_Type,
             stage_def.TaskStageDef_Description)
        )
        self.connection.commit()
    ##########################################################

    # Fetch Task Stage Def #############################
    def get_all_TaskStageDefs(self): # Retreive all Stages rows from the table
        """ Retrieves all TaskStageDef records from the database.
        Returns a list of TaskStageDef objects. """

        self.cursor.execute("SELECT * FROM TaskStageDef")
        rows = self.cursor.fetchall()
        return [
            TaskStageDef(
                row["TaskStageDef_ID"],
                row["TaskDef_ID_FK"],
                row["TaskStageDef_Type"],
                row["TaskStageDef_Description"]
            )
            for row in rows
        ]

    def get_TaskStageDefs_for_task(self, taskdef_id): # Fetch the stages of the task by Task Definition ID within the table
        """Returns all TaskStageDefs for a given TaskDef_ID_FK."""
        self.cursor.execute(
            "SELECT * FROM TaskStageDef WHERE TaskDef_ID_FK = ? ORDER BY TaskStageDef_ID",
            (taskdef_id,)
        )
        rows = self.cursor.fetchall()

        # A list must be returned for templates that loop over stages.
        return [
            TaskStageDef(
                r["TaskStageDef_ID"],
                r["TaskDef_ID_FK"],
                r["TaskStageDef_Type"],
                r["TaskStageDef_Description"]
            )
            for r in rows
        ]

    def get_TaskStageDef_by_id(self, stage_id): # Fetch the individual stage by using its ID from the table
        """Returns a single TaskStageDef by TaskStageDef_ID."""
        self.cursor.execute(
            "SELECT * FROM TaskStageDef WHERE TaskStageDef_ID = ?",
            (stage_id,)
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return TaskStageDef(
            row["TaskStageDef_ID"],
            row["TaskDef_ID_FK"],
            row["TaskStageDef_Type"],
            row["TaskStageDef_Description"]
        )
    ##########################################################

    # Update Task Stage Def #############################
    def update_TaskStageDef(self, stage_def): # Update an individual existing stage row (can be iterated)
        """ Updates an existing TaskStageDef record."""

        self.cursor.execute('''
            UPDATE TaskStageDef
            SET TaskDef_ID_FK = ?, TaskStageDef_Type = ?, TaskStageDef_Description = ?
            WHERE TaskStageDef_ID = ?
        ''', (stage_def.TaskDef_ID_FK,
              stage_def.TaskStageDef_Type,
              stage_def.TaskStageDef_Description,
              stage_def.TaskStageDef_ID))
        self.connection.commit()
    ##########################################################

    # Delete Task Stage Def #############################
    def delete_TaskStageDef(self, TaskStageDef_ID): # Delete an individual stage row
        """ Deletes a TaskStageDef record by its ID. """

        self.cursor.execute(
            "DELETE FROM TaskStageDef WHERE TaskStageDef_ID = ?",
            (TaskStageDef_ID,)
        )
        self.connection.commit()

    def delete_TaskStageDefs_for_task(self, taskdef_id): # Delete the stages associated with the task def (by using TaskDefID in the table column)
        """ Deletes all TaskStageDef records linked to a TaskDef_ID_FK. """

        self.cursor.execute(
            "DELETE FROM TaskStageDef WHERE TaskDef_ID_FK = ?",
            (taskdef_id,)
        )
        self.connection.commit()
    ##########################################################


    def close_connection(self):
        """ Closes the SQLite database connection. """
        self.connection.close()
