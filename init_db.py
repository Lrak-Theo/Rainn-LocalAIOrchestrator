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
    # CORE TEMPLATE TABLES
    # ------------------------------------------

    # TaskDef Table
    cursor.execute("""
        CREATE TABLE TaskDef (
            TaskDef_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TaskDef_Name TEXT NOT NULL UNIQUE,
            TaskDef_Description TEXT,
            isSystemCreated INTEGER NOT NULL DEFAULT 0 CHECK (isSystemCreated IN (0, 1))
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

    # AgentProcess Table
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
    # EXECUTION TRACEABILITY TABLES
    # ------------------------------------------

    # TaskInstance Table
    # One row per execution run:
    # "User ran AgentProcess Y using TaskDef Z at time T"
    cursor.execute("""
        CREATE TABLE TaskInstance (
            TaskInstance_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Process_ID_FK INTEGER NOT NULL,
            TaskDef_ID_FK INTEGER NOT NULL,
            Status TEXT CHECK(Status IN ('RUNNING', 'COMPLETED', 'FAILED')) NOT NULL,
            Run_Folder TEXT NOT NULL DEFAULT '',
            Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
            Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (Process_ID_FK) REFERENCES AgentProcess(Process_ID),
            FOREIGN KEY (TaskDef_ID_FK) REFERENCES TaskDef(TaskDef_ID)
        );
    """)

    # TaskStageInstance Table
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
        INSERT INTO TaskDef (TaskDef_Name, TaskDef_Description, isSystemCreated)
        VALUES (?, ?, ?)
    """, [
        (
            "GDPR SOC2 Compliance Risk Assessor",
            "Assess uploaded evidence for GDPR and SOC 2 control gaps, risks, and remediation priorities.",
            1
        ),
        (
            "Invoice Spend Graph Analyser (By Provider)",
            "Extract invoice spend data, structure it, and generate a visual chart by provider.",
            1
        ),
        (
            "Invoice Spend Graph Analyser (By Product / Service)",
            "Extract invoice spend data, structure it, and generate a visual chart by product service.",
            1
        ),
        (
            "Deadlines Risk Tracker",
            "Process given documents and list potential deadlines, sorted by urgency and risk.",
            1
        ),
        (
            "Procurement Quote Comparison Assistant",
            "Compare multiple vendor quotes and produce a structured shortlist by cost, terms, delivery risk, and recommendation.",
            1
        )
    ])

    # Fetch IDs for seeded TaskDefs
    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='GDPR SOC2 Compliance Risk Assessor'")
    gdpr_soc2_id = cursor.fetchone()[0]

    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='Invoice Spend Graph Analyser (By Provider)'")
    invoice_graph_provider_id = cursor.fetchone()[0]

    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='Invoice Spend Graph Analyser (By Product / Service)'")
    invoice_graph_product_service_id = cursor.fetchone()[0]

    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='Deadlines Risk Tracker'")
    deadlines_risk_tracker_id = cursor.fetchone()[0]

    cursor.execute("SELECT TaskDef_ID FROM TaskDef WHERE TaskDef_Name='Procurement Quote Comparison Assistant'")
    procurement_quote_comparison_id = cursor.fetchone()[0]

    # Seed Stages
    cursor.executemany("""
        INSERT INTO TaskStageDef (TaskDef_ID_FK, TaskStageDef_Type, TaskStageDef_Description)
        VALUES (?, ?, ?)
    """, [
        # GDPR SOC2 Compliance Risk Assessor
        (gdpr_soc2_id, "input",   "Read the uploaded compliance evidence and policy documents."),
        (gdpr_soc2_id, "extract", "Extract controls, data handling details, access controls, and incident response evidence."),
        (gdpr_soc2_id, "compare", "Map findings to GDPR principles and SOC 2 trust criteria, then identify gaps."),
        (gdpr_soc2_id, "format",  "Return ONLY raw CSV with columns: Framework,Control,Gap,Risk Level,Recommendation,Owner."),
        (gdpr_soc2_id, "output",  "Provide a concise remediation summary prioritised by risk."),

        # Invoice Spend Graph Analyser (By Provider)
        (invoice_graph_provider_id, "input",   "Read the uploaded invoices."),
        (invoice_graph_provider_id, "extract", "Extract invoice fields: invoice_id, date, provider, amount, currency, and line item."),
        (invoice_graph_provider_id, "format",  "Group spend by provider and return ONLY raw CSV with columns: Provider,Total Amount."),
        (invoice_graph_provider_id, "graph",   "Visualise provider totals using a chart."),

        # Invoice Spend Graph Analyser (By Product / Service)
        (invoice_graph_product_service_id, "input",   "Read the uploaded invoices."),
        (invoice_graph_product_service_id, "extract", "Extract invoice fields: invoice_id, date, product_or_service, amount, currency, and line item."),
        (invoice_graph_product_service_id, "format",  "Group spend by product_or_service and return ONLY raw CSV with columns: Product or Service,Total Amount."),
        (invoice_graph_product_service_id, "graph",   "Visualise product/service totals using a chart."),

        # Deadlines Risk Tracker
        (deadlines_risk_tracker_id, "input",   "Read uploaded task lists, emails, and planning documents."),
        (deadlines_risk_tracker_id, "extract", "Extract tasks, owners, deadlines, status, and dependencies."),
        (deadlines_risk_tracker_id, "compare", "Assess urgency and risk based on due date proximity, status, and blockers."),
        (deadlines_risk_tracker_id, "format",  "Return ONLY raw CSV with columns: Task,Owner,Deadline,Days Remaining,Risk Level,Next Action."),
        (deadlines_risk_tracker_id, "output",  "Provide a priority summary for the next 7, 14, and 30 days in the form of a table."),

        # Procurement Quote Comparison Assistant
        (procurement_quote_comparison_id, "input",   "Read uploaded vendor quotes and procurement requirements."),
        (procurement_quote_comparison_id, "extract", "Extract vendor, item, total cost, lead time, terms, and warranty details."),
        (procurement_quote_comparison_id, "compare", "Evaluate quotes by cost, delivery risk, and commercial terms."),
        (procurement_quote_comparison_id, "format",  "Return ONLY raw CSV with columns: Vendor,Total Cost,Delivery Risk,Commercial Terms Score,Recommendation."),
        (procurement_quote_comparison_id, "output",  "Provide a shortlist recommendation with rationale.")

    ])

    # Seed Agent Processes (pre-defined configured agents)
    cursor.executemany("""
        INSERT INTO AgentProcess (User_ID, Agent_Name, Agent_Priming, AI_Model, Operation_Selected)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (
            1,
            "GDPR SOC2 Compliance Risk Assessor",
            "You are a compliance risk analyst. Be evidence-based, concise, and prioritise remediation by risk impact.",
            "llama3.1:8b",
            gdpr_soc2_id
        ),
        (
            1,
            "Invoice Spend Graph Analyser (By Provider)",
            "You are a finance operations analyst. Keep outputs structured, numeric, and audit-friendly.",
            "qwen2.5:7b",
            invoice_graph_provider_id
        ),
        (
            1,
            "Invoice Spend Graph Analyser (By Product / Service)",
            "You are a finance operations analyst. Keep outputs structured, numeric, and audit-friendly.",
            "qwen2.5:7b",
            invoice_graph_product_service_id
        ),
        (
            1,
            "Deadlines Risk Tracker",
            "You are an operations coordinator. Prioritise urgent work, flag conflicts early, and produce clear action queues.",
            "gemma3:4b",
            deadlines_risk_tracker_id
        ),
        (
            1,
            "Procurement Quote Comparison Assistant",
            "You are a procurement analyst. Compare vendors objectively across cost, risk, and terms.",
            "gemma3:12b",
            procurement_quote_comparison_id
        ),
    ])

    conn.commit()
    conn.close()
    print("Rainn DB initialised.")


if __name__ == "__main__":
    init_db()
