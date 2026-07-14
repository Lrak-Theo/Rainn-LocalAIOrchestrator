Rainn
=====

Rainn is a guided workflow builder for creating, running, and managing document-processing agent plans. It lets a user define reusable multi-stage plans, upload files, run those plans through a local Ollama model, and view structured outputs such as summaries, CSV-style results, and generated charts.

![Flask UI - Home](Home.png)
![Plan screen](Plan%20select.png)
![Output screen](Output%20.png)

What It Does
------------

- Provides a chat-style interface for interacting with Rainn.
- Allows users to create custom agent plans made of ordered stages.
- Includes reusable starter plans for compliance review, invoice analysis, deadline tracking, and procurement comparison.
- Accepts uploaded files and normalises them into text for workflow processing.
- Runs each workflow stage in sequence and stores runtime progress.
- Shows live progress updates while a plan is running.
- Saves run artifacts so completed outputs can be viewed or downloaded.
- Supports importing and exporting reusable flow definitions as JSON.

Problem It Solves
-----------------

Many document-heavy tasks require the same repeated process: read files, extract important information, compare or evaluate it, format the result, and produce a final output. Rainn turns those repeated processes into reusable plans, so users can run structured workflows without manually prompting a model step by step each time, locally and privately.

The project is aimed at making local document automation easier for tasks such as:

- Compliance risk assessment
- Invoice spend analysis
- Deadline and workload tracking
- Procurement quote comparison
- Structured report generation

![Flask Plan list](Plan%20list.png)
![Flask run history](Plan%20history.png)

Tech Stack
----------

- Python
- Flask
- Flask-SocketIO
- SQLite
- Ollama local model API
- Requests
- Matplotlib
- python-docx
- PyPDF2
- HTML, CSS, and JavaScript
- Tabler UI styling
- Socket.IO for live progress updates

Project Structure
-----------------

- app.py: Main Flask application and route definitions.
- init_db.py: SQLite schema creation and seed data.
- backend/model: Data model classes.
- backend/dao: Database access layer.
- backend/service: Service layer for app logic.
- runtime_logic: Flow execution, stage prompting, file reading, and output handling.
- integrations: External/local integrations such as Ollama and chart rendering.
- import_export_logic: Flow import/export validation and conversion.
- templates: Flask/Jinja HTML templates.
- static: CSS and image assets.

Iterations
----------

The project was built across 6 iterations:

1. Core database models and basic task definition structure.
2. Agent process setup, allowing configured plans to be saved.
3. Runtime traceability with task instances and stage instances.
4. Flow import/export, chart rendering, and stronger output handling.
5. Interface improvements for browsing, viewing, and managing flows.
6. Chat-based workflow execution, live progress feedback, and improved user experience.
7. Final Demo to stakeholders (examiners)

Current Features
----------------

- Create, edit, delete, view, import, and export plans.
- Run selected plans directly from the chat page.
- Upload one or more files into a plan run.
- Track plan progress stage by stage.
- Render text, CSV, JSON, and SVG/chart outputs.
- Download generated run artifacts.
- Reset runtime instance data on startup for minimal data retention.

