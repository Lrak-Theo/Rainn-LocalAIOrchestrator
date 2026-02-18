# ==========================================
# File: app.py
# Updated in iteration: 4
# Author: Karl Concha
#
# Purpose:
# Flask entrypoint for Rainn (Guided AI Agent Builder).
#
# Iteration 3 Notes:
# - Runtime execution now creates TaskInstance + TaskStageInstance records
# - Uploaded files are normalised to text (Stage 0) and written to artifacts
# - DB view now includes TaskInstance and TaskStageInstance listings
# 
# Iteration 4 Notes:
# - Added flow import/export endpoints for reusable agent definitions.
# - Import now redirects back to My Flows with success/error messaging.
#
# #ChatGPT (OpenAI, 2025) – Assisted in refactoring Flask routing
# to use modular DAO + Service layers following supervisor
# feedback. Updated naming (Pipeline → Process) to match
# revised architecture and ERD in Iteration 2.
# Conversation Topic: "Rainn Iteration 2 – Modular Routing + Process Runner"
# Date: January 2026
# ==========================================

from flask import Flask, render_template, request, redirect, url_for, send_file, abort
import json
import io
import os
import shutil
import tempfile
import time
import zipfile

# ==========================================
# SERVICE IMPORTS
# ==========================================
from service.task_def_service import TaskDefService
from service.task_stage_def_service import TaskStageService
from service.agent_process_service import AgentProcessService
from runtime_logic.flow_runtime.flow_runtime import FlowRuntime
from service.task_instance_service import TaskInstanceService
from service.task_stage_instance_service import TaskStageInstanceService
from import_export_logic.flow_exchange_service import FlowExchangeService


# ==========================================
# INITIALISE APP + SERVICES
# ==========================================
app = Flask(__name__)

taskdef_service = TaskDefService()
stage_service = TaskStageService()
process_service = AgentProcessService()
agent_runtime = FlowRuntime()

# Iteration 3: instance tracking services (execution traceability)
task_instance = TaskInstanceService()
task_stage_instance = TaskStageInstanceService()
flow_exchange = FlowExchangeService()

RUN_TTL_SECONDS = 15 * 60
CLEANUP_INTERVAL_SECONDS = 60
RECEIPT_RETENTION_SECONDS = 6 * 60 * 60
RECEIPT_RETENTION_HOURS = RECEIPT_RETENTION_SECONDS // 3600
_last_cleanup_at = 0


def _safe_run_folder(task_instance_id):
    return os.path.join("agent_runs", str(task_instance_id))


def _delete_run_folder(task_instance_id):
    run_folder = _safe_run_folder(task_instance_id)
    if os.path.isdir(run_folder):
        shutil.rmtree(run_folder, ignore_errors=True)


def _cleanup_task_instance(task_instance_id):
    _delete_run_folder(task_instance_id)
    task_stage_instance.clear_outputs_for_task_instance(task_instance_id)
    task_instance.mark_deleted(task_instance_id)


def _cleanup_expired_runs():
    expired = task_instance.get_expired_task_instances()
    for ti in expired:
        _cleanup_task_instance(ti.TaskInstance_ID)

def _purge_old_receipts():
    old_receipts = task_instance.get_deleted_before(RECEIPT_RETENTION_SECONDS)
    for ti in old_receipts:
        task_stage_instance.delete_for_task_instance(ti.TaskInstance_ID)
        task_instance.hard_delete(ti.TaskInstance_ID)


@app.before_request
def _privacy_cleanup_guard():
    global _last_cleanup_at
    now = time.time()
    if now - _last_cleanup_at < CLEANUP_INTERVAL_SECONDS:
        return
    _last_cleanup_at = now
    _cleanup_expired_runs()
    _purge_old_receipts()


# ==========================================
# HOME / INDEX
# ==========================================
@app.route("/")
def home_page():
    """
    Displays all TaskDefs and their TaskStageDefs.
    Stages grouped by TaskDef_ID for clarity.
    """
    taskdefs = taskdef_service.list_taskdefs()
    stages = stage_service.list_all_stages()

    stages_by_agent = {}
    for st in stages:
        stages_by_agent.setdefault(st.TaskDef_ID_FK, []).append(st)

    return render_template(
        "index.html",
        taskdefs=taskdefs,
        stages_by_agent=stages_by_agent
    )


# ==========================================
# PROCESS LIST (Agent Test Page)
# ==========================================
@app.route("/test_agent")
def test_agent_page():
    """
    Shows the Agent Processes available in a page.
    """
    taskdefs = taskdef_service.list_taskdefs()
    taskdef_map = {t.TaskDef_ID: t for t in taskdefs}
    import_success = request.args.get("import_success")
    import_error = request.args.get("import_error")
    imported_process_id = request.args.get("process_id")
    return render_template(
        "flow_selection_page.html",
        processes=process_service.list_processes(),
        taskdef_map=taskdef_map,
        import_success=import_success,
        import_error=import_error,
        imported_process_id=imported_process_id
    )


# ==========================================
# FLOW IMPORT (Reusable Definitions)
# ==========================================
@app.route("/flow/import", methods=["GET", "POST"])
def flow_import_page():
    if request.method == "GET":
        return redirect(url_for("test_agent_page"))

    payload_raw = ""
    uploaded = request.files.get("flow_file")
    if uploaded and uploaded.filename:
        payload_raw = uploaded.read().decode("utf-8", errors="ignore")
    else:
        error_message = "Please choose a JSON file to import."
        return redirect(url_for("test_agent_page", import_error=error_message))

    if not payload_raw.strip():
        error_message = "Uploaded file is empty."
        return redirect(url_for("test_agent_page", import_error=error_message))
    if len(payload_raw) > 200000:
        error_message = "Payload too large. Please keep it under 200 KB."
        return redirect(url_for("test_agent_page", import_error=error_message))

    try:
        payload = json.loads(payload_raw)
    except Exception:
        payload = None
        error_message = "Invalid JSON."
        return redirect(url_for("test_agent_page", import_error=error_message))

    ok, err = flow_exchange.validate_flow_payload(payload)
    if not ok:
        error_message = (err or "Invalid flow payload.")
        error_message = error_message[:160]
        return redirect(url_for("test_agent_page", import_error=error_message))

    try:
        process_id = flow_exchange.import_flow(payload)
    except Exception as e:
        error_message = f"Import failed: {e}"
        error_message = error_message[:160]
        return redirect(url_for("test_agent_page", import_error=error_message))

    return redirect(url_for("test_agent_page", import_success=1, process_id=process_id))


# ==========================================
# FLOW EXPORT (Reusable Definitions)
# ==========================================
@app.route("/process/<int:process_id>/export")
def export_flow(process_id):
    flow_payload = flow_exchange.export_flow(process_id)
    if not flow_payload:
        return "Flow not found.", 404

    agent_name = (flow_payload["flow"].get("agent_name") or "flow").strip()
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in agent_name)
    filename = f"rainn_flow_{safe_name}_{process_id}.json"
    data = json.dumps(flow_payload, indent=2)
    return send_file(
        io.BytesIO(data.encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name=filename
    )


# ==========================================
# AGENT BUILDER (AgentProcess Creator)
# ==========================================
@app.route("/agent_builder", methods=["GET", "POST"])
def agent_builder_page():
    """
    Creates an AgentProcess (configured runnable agent).
    Uses the working zip-style create_process signature.
    """
    taskdefs = taskdef_service.list_taskdefs()
    process_service = AgentProcessService()
    processes = process_service.list_processes()
    name_by_taskdef = {}
    for p in processes:
        if getattr(p, "Operation_Selected", None) and getattr(p, "Agent_Name", None):
            name_by_taskdef[p.Operation_Selected] = p.Agent_Name
    template_taskdefs = []
    for t in taskdefs:
        if (t.TaskDef_Name or "").startswith("Custom -"):
            continue
        template_taskdefs.append({
            "TaskDef_ID": t.TaskDef_ID,
            "TaskDef_Name": t.TaskDef_Name,
            "TaskDef_Description": t.TaskDef_Description,
            "Display_Name": name_by_taskdef.get(t.TaskDef_ID, t.TaskDef_Name)
        })

    selected_taskdef = (
        request.args.get("operation_selected") or
        request.form.get("operation_selected")
    )

    stages = None
    if selected_taskdef:
        selected_taskdef = int(selected_taskdef)
        stages = stage_service.get_stages_for_task(selected_taskdef)

    agent_created = False
    saved_process_id = None
    edit_stages = []
    error_message = None
    step = "details"
    edit_process_id = None
    agent_name_val = request.form.get("agent_name") if request.method == "POST" else ""
    agent_priming_val = request.form.get("agent_priming") if request.method == "POST" else ""
    ai_model_val = request.form.get("ai_model") if request.method == "POST" else ""
    from_scratch_val = request.form.get("from_scratch") == "on" if request.method == "POST" else False

    raw_edit_id = request.args.get("edit_process_id") if request.method == "GET" else request.form.get("edit_process_id")
    if raw_edit_id:
        edit_process_id = int(raw_edit_id)

    if request.method == "GET" and edit_process_id:
        proc = process_service.get_process(edit_process_id)
        if proc:
            agent_name_val = proc.Agent_Name or ""
            agent_priming_val = proc.Agent_Priming or ""
            ai_model_val = proc.AI_Model or ""
            current_stages = stage_service.get_stages_for_task(proc.Operation_Selected)
            edit_stages = [
                (s.TaskStageDef_Type, s.TaskStageDef_Description)
                for s in current_stages
                if (s.TaskStageDef_Type or "").strip().lower() != "input"
            ]
            step = "stages"
            from_scratch_val = True

    def _normalize_stages(stage_names, stage_descs):
        normalized = []
        for s_name, s_desc in zip(stage_names, stage_descs):
            stage_type = (s_name or "").strip()
            stage_desc = (s_desc or "").strip()
            if not stage_type and not stage_desc:
                continue
            if stage_type.lower() == "input":
                continue
            normalized.append((stage_type, stage_desc))
        return normalized

    if request.method == "POST":
        action = request.form.get("action") or "save"
        from_scratch = request.form.get("from_scratch") == "on"

        if action == "next":
            step = "template"
            return render_template(
                "create_flow_page.html",
                taskdefs=taskdefs,
                template_taskdefs=template_taskdefs,
                stages=stages,
                selected_taskdef=selected_taskdef,
                agent_saved=agent_created,
                saved_process_id=saved_process_id,
                step=step,
                edit_stages=[],
                from_scratch=from_scratch,
                agent_name=agent_name_val,
                agent_priming=agent_priming_val,
                ai_model=ai_model_val,
                edit_process_id=edit_process_id
            )

        if action == "back_details":
            step = "details"
            return render_template(
                "create_flow_page.html",
                taskdefs=taskdefs,
                template_taskdefs=template_taskdefs,
                stages=stages,
                selected_taskdef=selected_taskdef,
                agent_saved=agent_created,
                saved_process_id=saved_process_id,
                step=step,
                edit_stages=[],
                from_scratch=from_scratch,
                agent_name=agent_name_val,
                agent_priming=agent_priming_val,
                ai_model=ai_model_val,
                edit_process_id=edit_process_id
            )

        if action == "choose_template":
            step = "stages"
            if not from_scratch and not selected_taskdef:
                error_message = "Choose a template or start from scratch."
                return render_template(
                    "create_flow_page.html",
                    taskdefs=taskdefs,
                    template_taskdefs=template_taskdefs,
                    stages=stages,
                    selected_taskdef=selected_taskdef,
                    agent_saved=agent_created,
                    saved_process_id=saved_process_id,
                    step="template",
                    edit_stages=[],
                    from_scratch=from_scratch,
                    agent_name=agent_name_val,
                    agent_priming=agent_priming_val,
                    ai_model=ai_model_val,
                    error_message=error_message,
                    edit_process_id=edit_process_id
                )
            if from_scratch:
                edit_stages = [
                    ("extract", "Extract the key points."),
                    ("output", "Present the final response for the user.")
                ]
            else:
                edit_stages = [
                    (s.TaskStageDef_Type, s.TaskStageDef_Description)
                    for s in stage_service.get_stages_for_task(selected_taskdef)
                    if (getattr(s, "TaskStageDef_Type", "") or "").strip().lower() != "input"
                ]
            return render_template(
                "create_flow_page.html",
                taskdefs=taskdefs,
                template_taskdefs=template_taskdefs,
                stages=stages,
                preview_stages=edit_stages,
                selected_taskdef=selected_taskdef,
                agent_saved=agent_created,
                saved_process_id=saved_process_id,
                step=step,
                edit_stages=edit_stages,
                from_scratch=from_scratch,
                agent_name=agent_name_val,
                agent_priming=agent_priming_val,
                ai_model=ai_model_val,
                edit_process_id=edit_process_id
            )

        if action in ("review", "back_template", "back_stages", "save"):
            stage_names = request.form.getlist("stage_name[]")
            stage_descs = request.form.getlist("stage_desc[]")
            has_custom = any(
                (n or "").strip() or (d or "").strip()
                for n, d in zip(stage_names, stage_descs)
            )
            if not from_scratch and selected_taskdef and not has_custom:
                blueprint_stage_objs = [
                    s for s in stage_service.get_stages_for_task(selected_taskdef)
                    if (getattr(s, "TaskStageDef_Type", "") or "").strip().lower() != "input"
                ]
                edit_stages = _normalize_stages(
                    [s.TaskStageDef_Type for s in blueprint_stage_objs],
                    [s.TaskStageDef_Description for s in blueprint_stage_objs]
                )
            else:
                edit_stages = _normalize_stages(stage_names, stage_descs)

        if action == "back_template":
            step = "template"
            return render_template(
                "create_flow_page.html",
                taskdefs=taskdefs,
                template_taskdefs=template_taskdefs,
                stages=stages,
                preview_stages=edit_stages,
                selected_taskdef=selected_taskdef,
                agent_saved=agent_created,
                saved_process_id=saved_process_id,
                step=step,
                edit_stages=edit_stages,
                from_scratch=from_scratch,
                agent_name=agent_name_val,
                agent_priming=agent_priming_val,
                ai_model=ai_model_val,
                edit_process_id=edit_process_id
            )

        if action == "review":
            if not from_scratch and not selected_taskdef:
                error_message = "Choose a template or start from scratch to continue."
                return render_template(
                    "create_flow_page.html",
                    taskdefs=taskdefs,
                    template_taskdefs=template_taskdefs,
                    stages=stages,
                    preview_stages=edit_stages,
                    selected_taskdef=selected_taskdef,
                    agent_saved=agent_created,
                    saved_process_id=saved_process_id,
                    step="stages",
                    edit_stages=edit_stages,
                    from_scratch=from_scratch,
                    agent_name=agent_name_val,
                    agent_priming=agent_priming_val,
                    ai_model=ai_model_val,
                    error_message=error_message,
                    edit_process_id=edit_process_id
                )
            step = "review"
            return render_template(
                "create_flow_page.html",
                taskdefs=taskdefs,
                template_taskdefs=template_taskdefs,
                stages=stages,
                preview_stages=edit_stages,
                selected_taskdef=selected_taskdef,
                agent_saved=agent_created,
                saved_process_id=saved_process_id,
                step=step,
                edit_stages=edit_stages,
                from_scratch=from_scratch,
                agent_name=agent_name_val,
                agent_priming=agent_priming_val,
                ai_model=ai_model_val,
                edit_process_id=edit_process_id
            )

        if action == "back_stages":
            step = "stages"
            return render_template(
                "create_flow_page.html",
                taskdefs=taskdefs,
                template_taskdefs=template_taskdefs,
                stages=stages,
                preview_stages=edit_stages,
                selected_taskdef=selected_taskdef,
                agent_saved=agent_created,
                saved_process_id=saved_process_id,
                step=step,
                edit_stages=edit_stages,
                from_scratch=from_scratch,
                agent_name=agent_name_val,
                agent_priming=agent_priming_val,
                ai_model=ai_model_val,
                edit_process_id=edit_process_id
            )

        agent_name = request.form.get("agent_name")
        agent_priming = request.form.get("agent_priming")
        ai_model = request.form.get("ai_model")

        edited_stages = edit_stages or _normalize_stages(
            request.form.getlist("stage_name[]"),
            request.form.getlist("stage_desc[]")
        )

        if edit_process_id:
            # Edit mode: update the existing process and replace its stages in-place
            proc = process_service.get_process(edit_process_id)
            proc.Agent_Name = agent_name
            proc.Agent_Priming = agent_priming
            proc.AI_Model = ai_model
            process_service.update_process(proc)
            stage_service.delete_stages_for_task(proc.Operation_Selected)
            for s_name, s_desc in edited_stages:
                stage_service.create_stage(proc.Operation_Selected, s_name, s_desc)
            agent_created = True
            saved_process_id = proc.Process_ID
        else:
            taskdef_id_to_use = selected_taskdef
            from_scratch = request.form.get("from_scratch") == "on"

            if from_scratch:
                base_name = (agent_name or "Custom Agent").strip()
                candidate_name = f"Custom - {base_name}"
                existing_names = {t.TaskDef_Name for t in taskdefs}
                if candidate_name in existing_names:
                    suffix = 1
                    while f"{candidate_name} ({suffix})" in existing_names:
                        suffix += 1
                    candidate_name = f"{candidate_name} ({suffix})"

                taskdef_id_to_use = taskdef_service.create_taskdef(
                    candidate_name,
                    "Custom template created by user."
                )
                for s_name, s_desc in edited_stages:
                    stage_service.create_stage(taskdef_id_to_use, s_name, s_desc)
            else:
                if not selected_taskdef:
                    error_message = "Select a blueprint template or choose 'Start from scratch' to save."
                    return render_template(
                        "create_flow_page.html",
                        taskdefs=taskdefs,
                        template_taskdefs=template_taskdefs,
                        stages=stages,
                        selected_taskdef=selected_taskdef,
                        agent_saved=agent_created,
                        saved_process_id=saved_process_id,
                        step="stages",
                        edit_stages=edit_stages,
                        from_scratch=from_scratch,
                        agent_name=agent_name_val,
                        agent_priming=agent_priming_val,
                        ai_model=ai_model_val,
                        error_message=error_message,
                        edit_process_id=edit_process_id
                    )
                base_name = (agent_name or "Custom Agent").strip()
                candidate_name = f"Custom - {base_name}"
                existing_names = {t.TaskDef_Name for t in taskdefs}
                if candidate_name in existing_names:
                    suffix = 1
                    while f"{candidate_name} ({suffix})" in existing_names:
                        suffix += 1
                    candidate_name = f"{candidate_name} ({suffix})"

                taskdef_id_to_use = taskdef_service.create_taskdef(
                    candidate_name,
                    "Custom template created by user."
                )
                for s_name, s_desc in edited_stages:
                    stage_service.create_stage(taskdef_id_to_use, s_name, s_desc)

            # IMPORTANT:
            # Keep the zip version signature (required by the current service contract).
            new_process = process_service.create_process(
                user_id=1,
                agent_name=agent_name,
                agent_priming=agent_priming,
                taskdef_id=taskdef_id_to_use,
                ai_model=ai_model
            )
            agent_created = True
            saved_process_id = new_process.Process_ID

        step = "review"

    preview_stages = None
    if edit_stages:
        preview_stages = edit_stages
    elif stages:
        preview_stages = [
            (s.TaskStageDef_Type, s.TaskStageDef_Description)
            for s in stages
            if (getattr(s, "TaskStageDef_Type", "") or "").strip().lower() != "input"
        ]

    return render_template(
        "create_flow_page.html",
        taskdefs=taskdefs,
        template_taskdefs=template_taskdefs,
        stages=stages,
        preview_stages=preview_stages,
        selected_taskdef=selected_taskdef,
        agent_saved=agent_created,
        saved_process_id=saved_process_id,
        step=step,
        edit_stages=edit_stages,
        from_scratch=from_scratch_val,
        agent_name=agent_name_val if agent_created else agent_name_val,
        agent_priming=agent_priming_val if agent_created else agent_priming_val,
        ai_model=ai_model_val if agent_created else ai_model_val,
        error_message=error_message,
        edit_process_id=edit_process_id
    )


# ==========================================
# AGENT RUNTIME — RUN PROCESS (Iteration 3)
# ==========================================
@app.route("/agent_runner/<int:process_id>", methods=["GET", "POST"])
def agent_runner_page(process_id):
    """
    Executes a selected AgentProcess against a user-uploaded file.

    Iteration 3 runtime behaviour:
    - Creates TaskInstance record (RUNNING)
    - Stage 0 normalises input to text and writes 00_input_original.txt
    - Executes stage 1..N sequentially (stop on first failure)
    - Writes per-stage artifacts and persists paths in TaskStageInstance
    - Marks TaskInstance COMPLETED/FAILED accordingly
    """
    process = process_service.get_process(process_id)
    if not process:
        return "Agent Process not found.", 404

    taskdef = taskdef_service.get_taskdef_by_id(process.Operation_Selected)
    stages = stage_service.get_stages_for_task(taskdef.TaskDef_ID)

    file_text = None
    output_type = None
    output_artifact = None
    output_task_instance_id = None
    output_artifact_name = None
    stage_outputs = []
    run_active = False
    receipt = None
    receipt_message = None
    expires_in_minutes = None

    if request.method == "POST":
        uploaded_files = request.files.getlist("uploaded_file")

        if not uploaded_files:
            file_text = "No file uploaded"
        else:
            temp_files = []
            try:
                for uploaded in uploaded_files:
                    if not uploaded or not uploaded.filename:
                        continue
                    ext = os.path.splitext(uploaded.filename)[1]
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    tmp.write(uploaded.read())
                    tmp.flush()
                    tmp.close()
                    temp_files.append({
                        "path": tmp.name,
                        "name": uploaded.filename
                    })

                if not temp_files:
                    file_text = "No file uploaded"
                else:
                    result = agent_runtime.run_flow(
                        process_id=process_id,
                        taskdef_id=taskdef.TaskDef_ID,
                        file_path=temp_files
                    )  # Iteration 3 changes here to accommodate instances
                    if isinstance(result, dict):
                        file_text = result.get("output_text")
                        output_type = result.get("output_type")
                        output_artifact = result.get("output_artifact_path")
                        output_task_instance_id = result.get("task_instance_id")
                        if output_artifact:
                            output_artifact_name = os.path.basename(output_artifact)
                        if output_task_instance_id:
                            task_inst = task_instance.get_task_instance(output_task_instance_id)
                            if task_inst and task_instance.is_active(task_inst):
                                run_active = True
                                task_instance.touch_task_instance(output_task_instance_id, RUN_TTL_SECONDS)
                                task_inst = task_instance.get_task_instance(output_task_instance_id)
                                if task_inst and task_inst.Expires_At:
                                    expires_in_minutes = RUN_TTL_SECONDS // 60
                                stage_instances = task_stage_instance.get_stages_for_task_instance(output_task_instance_id)
                                for st in stage_instances:
                                    if not st.Output_Artifact_Path:
                                        continue
                                    artifact_name = os.path.basename(st.Output_Artifact_Path)
                                    ext = os.path.splitext(artifact_name)[1].lower()
                                    out_type = "text"
                                    if ext == ".svg":
                                        out_type = "svg"
                                    elif ext == ".csv":
                                        out_type = "csv"
                                    elif ext == ".json":
                                        out_type = "json"
                                    preview_text = None
                                    preview_truncated = False
                                    if out_type in ("text", "csv", "json"):
                                        try:
                                            max_chars = 4000
                                            with open(st.Output_Artifact_Path, "r", encoding="utf-8") as f:
                                                preview_text = f.read(max_chars + 1)
                                            if preview_text and len(preview_text) > max_chars:
                                                preview_text = preview_text[:max_chars]
                                                preview_truncated = True
                                        except Exception:
                                            preview_text = None
                                    stage_outputs.append({
                                        "order": st.Stage_Order,
                                        "name": st.Stage_Name,
                                        "artifact_name": artifact_name,
                                        "output_type": out_type,
                                        "task_instance_id": output_task_instance_id,
                                        "preview_text": preview_text,
                                        "preview_truncated": preview_truncated
                                    })
                                stage_outputs.sort(key=lambda x: x["order"])
                            else:
                                if task_inst and not task_inst.Deleted_At:
                                    _cleanup_task_instance(output_task_instance_id)
                                    task_inst = task_instance.get_task_instance(output_task_instance_id)
                                receipt = task_inst
                                receipt_message = "This run was automatically deleted for privacy after inactivity."
                    else:
                        file_text = result
            except Exception as e:
                file_text = f"Error: {e}"
            finally:
                for f in temp_files:
                    try:
                        os.remove(f["path"])
                    except Exception:
                        pass

    return render_template(
        "flow_viewer_page.html",
        process=process,
        taskdef=taskdef,
        stages=stages,
        file_text=file_text,
        output_type=output_type,
        output_artifact=output_artifact,
        output_task_instance_id=output_task_instance_id,
        output_artifact_name=output_artifact_name,
        stage_outputs=stage_outputs,
        run_active=run_active,
        receipt=receipt,
        message=receipt_message,
        expires_in_minutes=expires_in_minutes,
        receipt_retention_hours=RECEIPT_RETENTION_HOURS
    )



# ==========================================
# DELETE AGENT PROCESS
# ==========================================
@app.route("/delete_process/<int:process_id>", methods=["POST"])
def delete_process(process_id):
    """
    Deletes an AgentProcess.
    """
    process_service.delete_process(process_id)
    return redirect(url_for("test_agent_page"))


# ==========================================
# RUN ARTIFACT ZIP DOWNLOAD
# ==========================================
@app.route("/download_run/<int:task_instance_id>", methods=["POST"])
def download_run(task_instance_id):
    task_inst = task_instance.get_task_instance(task_instance_id)
    if not task_inst or not task_instance.is_active(task_inst):
        if task_inst and not task_inst.Deleted_At:
            _cleanup_task_instance(task_instance_id)
        return redirect(url_for("test_agent_page"))

    task_instance.mark_downloaded(task_instance_id, RUN_TTL_SECONDS)
    task_inst = task_instance.get_task_instance(task_instance_id)

    run_folder = _safe_run_folder(task_instance_id)
    if not os.path.isdir(run_folder):
        return redirect(url_for("test_agent_page"))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(run_folder):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, run_folder)
                zf.write(file_path, rel_path)
        metadata = {
            "task_instance_id": task_inst.TaskInstance_ID,
            "process_id": task_inst.Process_ID_FK,
            "taskdef_id": task_inst.TaskDef_ID_FK,
            "created_at": task_inst.Created_At,
            "last_accessed_at": task_inst.Last_Accessed_At,
            "expires_at": task_inst.Expires_At,
            "downloaded_at": task_inst.Downloaded_At
        }
        zf.writestr("run_metadata.json", json.dumps(metadata, indent=2))

    buffer.seek(0)
    filename = f"rainn_run_{task_instance_id}.zip"
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename
    )


# ==========================================
# RUN MANUAL DELETE
# ==========================================
@app.route("/delete_run/<int:task_instance_id>", methods=["POST"])
def delete_run(task_instance_id):
    task_inst = task_instance.get_task_instance(task_instance_id)
    if task_inst and not task_inst.Deleted_At:
        _cleanup_task_instance(task_instance_id)
    return redirect(url_for("test_agent_page"))


# ==========================================
# ARTIFACT FILE SERVER (Iteration 4 prep)
# ==========================================
@app.route("/artifact/<int:task_instance_id>/<path:filename>")
def artifact_file(task_instance_id, filename):
    """
    Serves artifact files from agent_runs/<id>/artifacts for inline display.
    """
    task_inst = task_instance.get_task_instance(task_instance_id)
    if not task_inst or not task_instance.is_active(task_inst):
        if task_inst and not task_inst.Deleted_At:
            _cleanup_task_instance(task_instance_id)
        return "Run has expired or been deleted.", 410

    task_instance.touch_task_instance(task_instance_id, RUN_TTL_SECONDS)

    artifacts_dir = os.path.join("agent_runs", str(task_instance_id), "artifacts")
    base_dir = os.path.abspath(artifacts_dir)
    requested_path = os.path.abspath(os.path.join(artifacts_dir, filename))

    if not requested_path.startswith(base_dir + os.sep):
        abort(404)

    if not os.path.exists(requested_path):
        abort(404)

    if requested_path.lower().endswith(".svg"):
        return send_file(requested_path, mimetype="image/svg+xml")

    return send_file(requested_path)
