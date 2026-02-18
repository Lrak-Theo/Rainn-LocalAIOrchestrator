# ==========================================
# File: task_stage_def_dao.py
# Updated in iteration: 4
# Author: Karl Concha
#
# #ChatGPT (OpenAI, 2025) – Assisted in structuring CRUD methods for TaskStageDefDAO
# and ensuring compliance with the UCC FYP Bible documentation requirements.
# Conversation Topic: "Rainn Iteration 1 – Database CRUD setup for linked TaskStageDef table"
# Date: November 2025
#
# References:
# - SQLite Documentation – "Python SQLite3 Module" (https://docs.python.org/3/library/sqlite3.html)
# - Tutorial adapted: “CRUD Operations using SQLite3 in Python” – GeeksForGeeks
#   (https://www.geeksforgeeks.org/python-sqlite/)
# ==========================================

import sqlite3
from model.task_stage_def import TaskStageDef


class TaskStageDefDAO:

    def __init__(self, db_name="rainn.db"):
        """ Initializes the connection to the SQLite database. """

        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

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

    def get_all_TaskStageDefs(self):
        """ Retrieves all TaskStageDef records from the database.
        Returns a list of TaskStageDef objects.
        ChatGPT assisted in list comprehension for object mapping. """

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

    def get_TaskStageDefs_for_task(self, taskdef_id):
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

    def get_TaskStageDef_by_id(self, stage_id):
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


    def update_TaskStageDef(self, stage_def):
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

    def delete_TaskStageDef(self, TaskStageDef_ID):
        """ Deletes a TaskStageDef record by its ID. """

        self.cursor.execute(
            "DELETE FROM TaskStageDef WHERE TaskStageDef_ID = ?",
            (TaskStageDef_ID,)
        )
        self.connection.commit()

    def close_connection(self):
        """ Closes the SQLite database connection. """
        self.connection.close()
