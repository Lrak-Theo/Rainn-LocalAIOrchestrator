import sqlite3
from backend.model.task_def import TaskDef

class TaskDefDAO:  

    def __init__(self, db_name="rainn.db"):
        """ Initializes the connection to the SQLite database. """

        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    # Create a Task definition #####################
    def add_TaskDef(self, task_def):
        """ Inserts a new TaskDef record into the database. """

        self.cursor.execute(
            '''INSERT INTO TaskDef (TaskDef_Name, TaskDef_Description, isSystemCreated)
               VALUES (?, ?, ?)''',
            (task_def.TaskDef_Name, task_def.TaskDef_Description, int(getattr(task_def, "isSystemCreated", 0)))
        )
        self.connection.commit()

        task_def.TaskDef_ID = self.cursor.lastrowid
        return task_def
    #############################################

    # Retreive Task definition(s) ########################
    def get_all_TaskDefs(self): # Fetch all
        """ Retrieves all TaskDef records from the database.
        Returns a list of TaskDef objects. """

        self.cursor.execute("SELECT * FROM TaskDef")
        rows = self.cursor.fetchall()
        return [
            TaskDef(
                row["TaskDef_ID"],
                row["TaskDef_Name"],
                row["TaskDef_Description"],
                row["isSystemCreated"]
            )
            for row in rows
        ]

    def get_TaskDef_by_id(self, TaskDef_ID): # Fetch by ID
        """ Retrieves a TaskDef record by its ID. """

        self.cursor.execute("SELECT * FROM TaskDef WHERE TaskDef_ID = ?", (TaskDef_ID,))
        row = self.cursor.fetchone()
        if row:
            return TaskDef(
                row["TaskDef_ID"],
                row["TaskDef_Name"],
                row["TaskDef_Description"],
                row["isSystemCreated"]
            )
        else:
            return None
    #############################################

    # Update Task definition ####################
    def update_TaskDef(self, task_def):
        """ Updates an existing TaskDef record. """

        self.cursor.execute('''
            UPDATE TaskDef
            SET TaskDef_Name = ?, TaskDef_Description = ?
            WHERE TaskDef_ID = ?
        ''', (task_def.TaskDef_Name, task_def.TaskDef_Description, task_def.TaskDef_ID))
        self.connection.commit()
    #############################################

    # Delete a Task definition ####################
    def delete_TaskDef(self, TaskDef_ID):
        """ Deletes a TaskDef record by its ID. """
        self.cursor.execute("DELETE FROM TaskDef WHERE TaskDef_ID = ?", (TaskDef_ID,))
        self.connection.commit()

    def close_connection(self):
        """ Closes the SQLite database connection. """
        self.connection.close()
     #############################################
