# ==========================================
# File: init_db.py
# Updated in iteration: 4
# Author: Karl Concha
#
# Purpose:
# Initialises the Rainn SQLite database schema.
# Iteration 3 updates introduce execution traceability tables:
# - TaskInstance (one per agent run)
# - TaskStageInstance (one per stage execution within a run)
#
# #ChatGPT (OpenAI, 2025) – Assisted in validating the Iteration 3 schema
# updates by correcting foreign key targets, drop/create ordering, and
# ensuring the TaskInstance/TaskStageInstance tables support artifact
# traceability and stop-on-failure runtime behaviour.
# Conversation Topic: "DB Schema for TaskInstance and TaskStageInstance"
# Date: January 2026
# ==========================================

import sqlite3


def init_db():
    conn = sqlite3.connect("rainn.db")
    cursor = conn.cursor()

    # Recommended for SQLite: enforce FK constraints (OFF by default in SQLite).
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ------------------------------------------
    # DROP OLD TABLES
    # Drop children first (tables with foreign keys) to avoid FK drop errors.
    # ------------------------------------------
    cursor.execute("DROP TABLE IF EXISTS TaskStageInstance;")
    cursor.execute("DROP TABLE IF EXISTS TaskInstance;")
    cursor.execute("DROP TABLE IF EXISTS TaskStageDef;")
    cursor.execute("DROP TABLE IF EXISTS AgentProcess;")
    cursor.execute("DROP TABLE IF EXISTS TaskDef;")

    # ------------------------------------------
    # CORE TEMPLATE TABLES (Iteration 1/2)
    # ------------------------------------------

    # TaskDef Table
    cursor.execute("""
        CREATE TABLE TaskDef (
            TaskDef_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TaskDef_Name TEXT NOT NULL UNIQUE,
            TaskDef_Description TEXT
        );
    """)

    # TaskStageDef Table
    cursor.execute("""
        CREATE TABLE TaskStageDef (
            TaskStageDef_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TaskDef_ID_FK INTEGER NOT NULL,
            TaskStageDef_Type TEXT NOT NULL,
            TaskStageDef_Description TEXT,
            FOREIGN KEY (TaskDef_ID_FK) REFERENCES TaskDef(TaskDef_ID)
        );
    """)

    # AgentProcess Table (Iteration 2)
    # Represents a saved "configured agent" with model + priming + selected template.
    cursor.execute("""
        CREATE TABLE AgentProcess (
            Process_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            User_ID INTEGER,
            Agent_Name TEXT,
            Agent_Priming TEXT DEFAULT NULL,
            AI_Model TEXT,
            Operation_Selected INTEGER NOT NULL,
            Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (Operation_Selected) REFERENCES TaskDef(TaskDef_ID)
        );
    """)

    # ------------------------------------------
    # EXECUTION TRACEABILITY TABLES (Iteration 3)
    # ------------------------------------------

    # TaskInstance Table (NEW Iteration 3)
    # One row per execution run:
    # "User ran AgentProcess Y using TaskDef Z at time T"
    cursor.execute("""
        CREATE TABLE TaskInstance (
            TaskInstance_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Process_ID_FK INTEGER NOT NULL,
            TaskDef_ID_FK INTEGER NOT NULL,
            Status TEXT CHECK(Status IN ('RUNNING', 'COMPLETED', 'FAILED')) NOT NULL,
            Run_Folder TEXT NOT NULL DEFAULT '',
            Last_Accessed_At DATETIME,
            Expires_At DATETIME,
            Deleted_At DATETIME,
            Downloaded_At DATETIME,
            Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
            Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (Process_ID_FK) REFERENCES AgentProcess(Process_ID),
            FOREIGN KEY (TaskDef_ID_FK) REFERENCES TaskDef(TaskDef_ID)
        );
    """)

    # TaskStageInstance Table (NEW Iteration 3)
    # One row per stage execution within a TaskInstance.
    cursor.execute("""
        CREATE TABLE TaskStageInstance (
            TaskStageInstance_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TaskInstance_ID_FK INTEGER NOT NULL,
            Stage_Order INTEGER NOT NULL,
            Stage_Name TEXT NOT NULL,
            Status TEXT CHECK(Status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')) NOT NULL,
            Output_Artifact_Path TEXT,
            Started_At DATETIME,
            Ended_At DATETIME,
            Error_Message TEXT,

            FOREIGN KEY (TaskInstance_ID_FK) REFERENCES TaskInstance(TaskInstance_ID)
        );
    """)

    # ------------------------------------------
    # SEED DATA (DEV / DEMO)
    # ------------------------------------------
    cursor.executemany("""
        INSERT INTO TaskDef (TaskDef_Name, TaskDef_Description)
        VALUES (?, ?)
    """, [
        (
            "research_paper_analyser_and_insight_gatherer",
            "You are a graduate student. Your task is to analyse the given research papers and follow the set instructions in each stages to gather important points."
        ),
        (
            "law_and_compliance_extractor",
            "You are a senior legal analyst working in a corporate law firm. You are tasked with extracting key compliances and clauses and to process them in a process."
        ),
        (
            "invoice_cleaner",
            "You are an accountant working in a FinTech company. Your job is to read through all the given invoices in many formats and to seperate and group them based on the given instructions."
        )
    ])

    # Fetch IDs for seeded TaskDefs
    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='research_paper_analyser_and_insight_gatherer'")
    research_paper_id = cursor.fetchone()[0]

    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='law_and_compliance_extractor'")
    law_compliance_id = cursor.fetchone()[0]

    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='invoice_cleaner'")
    invoice_cleaner_id = cursor.fetchone()[0]

    # Seed Stages
    cursor.executemany("""
        INSERT INTO TaskStageDef (TaskDef_ID_FK, TaskStageDef_Type, TaskStageDef_Description)
        VALUES (?, ?, ?)
    """, [
        # Research paper analyser (4 stages)
        (research_paper_id, "input", "Receive research papers in text or PDF form."),
        (research_paper_id, "extract", "Extract key points: claims, methods, datasets, and metrics."),
        (research_paper_id, "compare", "Compare papers for themes, agreements, and disagreements."),
        (research_paper_id, "output", "Provide a concise summary of insights."),

        # Law and compliance extractor (3 stages)
        (law_compliance_id, "input", "Receive legal/compliance documents."),
        (law_compliance_id, "extract", "Extract key clauses, obligations, parties, and regulations."),
        (law_compliance_id, "output", "Provide a concise compliance summary with any risks."),

        # Invoice cleaner (5 stages)
        (invoice_cleaner_id, "input", "Receive invoice files in multiple formats."),
        (invoice_cleaner_id, "extract", "Extract vendor, invoice numbers, dates, totals, and line items."),
        (invoice_cleaner_id, "validate", "Check totals, missing fields, and inconsistencies."),
        (invoice_cleaner_id, "format", "Group and format cleaned invoice data into a table."),
        (invoice_cleaner_id, "graph", "Visualise the findings using a graph"),
    ])

    # Seed Agent Processes (pre-defined configured agents)
    cursor.executemany("""
        INSERT INTO AgentProcess (User_ID, Agent_Name, Agent_Priming, AI_Model, Operation_Selected)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (
            1,
            "Research Paper Analyser and Insight Gatherer",
            "You are a graduate student. Your task is to analyse the given research papers and follow the set instructions in each stages to gather important points.",
            "llama3.1:8b",
            research_paper_id
        ),
        (
            1,
            "Law and Compliance Extractor",
            "You are a senior legal analyst working in a corporate law firm. You are tasked with extracting key compliances and clauses and to process them in a process.",
            "llama3.1:8b",
            law_compliance_id
        ),
        (
            1,
            "Invoice Cleaner",
            "You are an accountant working in a FinTech company. Your job is to read through all the given invoices in many formats and to seperate and group them based on the given instructions.",
            "llama3.1:8b",
            invoice_cleaner_id
        ),
    ])

    conn.commit()
    conn.close()
    print("Rainn DB initialised (Iteration 3 schema: AgentProcess + Instance traceability).")


if __name__ == "__main__":
    init_db()
