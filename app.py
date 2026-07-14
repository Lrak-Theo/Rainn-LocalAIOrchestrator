from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from flask_socketio import SocketIO
import json, io, os, shutil, tempfile

from backend.service.task_def_service import TaskDefService
from backend.service.task_stage_def_service import TaskStageService
from backend.service.agent_process_service import AgentProcessService
from runtime_logic.flow_runtime.flow_runtime import FlowRuntime
from backend.service.task_instance_service import TaskInstanceService
from backend.service.task_stage_instance_service import TaskStageInstanceService
from import_export_logic.flow_exchange_service import FlowExchangeService
from integrations.model_client_ollama import OllamaModelClient



# INITIALISE APP + SERVICES ##################################

app = Flask(__name__)
# The code below for initialising SocketIO and running the flow as a background task is adapted from:
# https://www.youtube.com/watch?v=bUfUKtJqaxQ
# I adapted it to pass the socketio instance into the flow runtime so stages can emit progress events.


socketio = SocketIO(app, async_mode='threading') # Responsible for enabling flow feedback

taskdef_service = TaskDefService()
stage_service = TaskStageService()
process_service = AgentProcessService()

# Instance tracking services
task_instance = TaskInstanceService()
task_stage_instance = TaskStageInstanceService()

# Flow import export 
flow_exchange = FlowExchangeService()

# Flow execution as 'flow_runtime'
flow_runtime = FlowRuntime(TaskInstanceService, TaskStageInstanceService, AgentProcessService, TaskDefService, TaskStageService)

# Chat integration as 'chat_client'
chat_client = OllamaModelClient()

####################################################################



# App functions  ####################################

# Layer 1 of minimal data retention: Taskinstance rows wiped out before system starts
def system_start_taskinstance_wipe():
    if os.path.exists("agent_runs"):
        shutil.rmtree("agent_runs") # Check if folder path exists, if yes remove including nested

    os.makedirs("agent_runs", exist_ok=True) # Create fresh agent_runs folder after

    task_stage_instance.delete_all() # Delete all instance stage
    task_instance.delete_all() # Delete all instance rows

system_start_taskinstance_wipe() # Call the function before system starts

def api_error(error_code, message, status=400, field=None): # Standardising error handling for API and DAOS under one function
    payload = {"ok": False, "error_code": error_code, "message": message}

    if field:
        payload["field"] = field

    return jsonify(payload), status


def normalize_stages(stage_names, stage_descs):
    normalized = []
    for s_name, s_desc in zip(stage_names, stage_descs):
        stage_type = (s_name or "").strip()
        stage_desc = (s_desc or "").strip()

        if not stage_type and not stage_desc:
            continue
        if not stage_type or not stage_desc:
            continue

        normalized.append((stage_type, stage_desc))
    return normalized


def next_available_taskdef_name(base_name):
    """Return a unique TaskDef name using numeric suffixes when needed."""
    clean_base = (base_name or "").strip() or "Untitled Plan"
    existing_names = {(t.TaskDef_Name or "").strip() for t in taskdef_service.list_taskdefs()}

    if clean_base not in existing_names:
        return clean_base

    i = 1
    while f"{clean_base} ({i})" in existing_names:
        i += 1

    return f"{clean_base} ({i})"


# This function preserves what the user typed when validation fails, so the form rerenders without losing input (USED IN EDIT FLOWS)
def stage_rows_for_form(stage_names, stage_descs):
    """Preserve user-entered rows (including partial rows) for re-render."""
    rows = []
    for s_name, s_desc in zip(stage_names, stage_descs):
        stage_type = (s_name or "").strip()
        stage_desc = (s_desc or "").strip()
        if not stage_type and not stage_desc:
            continue
        rows.append((stage_type, stage_desc))
    return rows

####################################################################


### SIDEBAR TREE ####################################################################################

# HOMEPAGE / LANDING PAGE
@app.route("/") 
def home_page():
    return render_template("chat_page.html")

############# Chat Routes ####################################

# SEND A MESSAGE TO THE AI MODEL
@app.route("/chat/send", methods=["POST"])
def chat_send(): 

    # Read the incoming HTTP request body as JSON and return it as a Python object to be used (a dict)
    data = request.get_json()

    # Get the assgined value of the "message" key from 'data' (the dict)
    user_message = data.get("message").strip()

    # Get the assigned value of the "context" key from 'data' (the dict)
    context = data.get("context", [])

    # Get the assigned value of the "flow context" key from 'data' (the dict)
    flow_context = (data.get("flow_context") or "").strip()

    # Create a context window list
    context_window = []

    # Looping the list of 'context'
    for x in context:
        # Get the 'role' value & 'content value
        role = x.get("role")
        content = x.get("content")

        # If the role contains "user" or "assistant" and has content value...
        if role in ("user", "assistant") and content:
            # Add the role and content values to the context_window list as a dictionary list value
            context_window.append({"role": role, "content": content[:1000]})

    # After gathering the context, assign a system prompt value
    system_prompt = "You are Rainn, a concise AI chat agent. You have ability to run flows in the form of 'plans'."
    
    # If flow_context has a value
    if flow_context:
        flow_context = flow_context[:6000]

        # Assign a specific flow system prompt instead
        system_prompt = (
            system_prompt
            + "\n\nYou have internal flow-run context from a prior plan execution."
            + "\nUse it to answer the user's question directly."
            + "\nDo not dump, quote, or list the raw flow context unless the user explicitly asks for it."
            + f"\n\nFLOW_CONTEXT:\n{flow_context}"
        )


    # After gathering the context and assigning a system prompt, begin to send the payload into Ollama client
    try:
        # Pass all the values assigned here 
        response_message = chat_client.generate(
            model_name="gemma3:12b", prompt=user_message, system_prompt=system_prompt,
            context=context_window)
        
        # send the repsonse_message to the HTTP by using a JSON body
        return jsonify({"response": response_message})
    
    # When an exception or error occurs, use the api_error function to send the type of issue to the frontend
    except Exception:
        return api_error("CHAT_SEND_FAILED", "Failed to generate chat response", 500)

#       |
#       |  ... Click 'plans' (button)
#       V

# FLOW PANEL INSIDE THE CHAT 
@app.route("/chat/flows", methods=["GET"]) 
def chat_list_flows():
    try:
        
        # Retrieve all the agent processes / flows and task defs from the database 
        processes = process_service.list_processes()
        taskdefs = taskdef_service.list_taskdefs()

        # Creating a dictionary where ID is the key for the object itself
        taskdef_dict = {t.TaskDef_ID :t for t in taskdefs} 

        # Create a flow list 
        flow_list = []
        
        # Loop the process / flows in the processes value (list var)
        for process in processes:

            # By getting the ID number of the operation_selected (the tasked fk), we can find the name by looking up the same ID in the dict
            taskdef = taskdef_dict.get(process.Operation_Selected) 

            # Also create a stages list 
            stages = []

            # If taskdef holds a value...
            if taskdef:

                # Get the stages of that stage def by using the task defintion ID (above)
                stage_defs = stage_service.get_stages_for_task(taskdef.TaskDef_ID)

                # Add the stages in the form of a dictionary containing keys of "type" (the title) and "desc" (the instruction)
                for stage in stage_defs:
                    stage_type = (stage.TaskStageDef_Type or "").strip()

                    stages.append({
                        "type": stage_type,
                        "desc": (stage.TaskStageDef_Description or "").strip()
                    })

            # Finally, populate the flow_list containing the needed process information and its associated stages (the stages list (which contains the dictionary values)) to show in the frontend
            flow_list.append({
                "process_id": process.Process_ID,
                "agent_name": process.Agent_Name,
                "ai_model": process.AI_Model,
                "stages": stages
            })

        # The flow list array is now populated and now sent as a JSON HTTP response back to the JS script to be used
        return jsonify({"flows": flow_list}) 
    
    # If Exception occurs, use the api_error function for error handling
    except Exception:
        return api_error("FLOW_LIST_FAILED", "Failed to load flows.", 500)

#       |
#       | 
#       V

# RUN THE SELECTED FLOW IN THE FLOW PANEL
@app.route("/chat/run_flow", methods=["POST"])
def chat_run_flow():

    # Retrieve the process desired by fetching the process_id from the HTML element
    process_id = request.form.get("process_id", type=int) 
    if not process_id: # Error handling
        return api_error("PROCESS_ID_REQUIRED", "process_id is required", 422, "process_id")

    # Afterwards get the process row from the database by using the process_id found
    process = process_service.get_process(process_id)
    if not process: # Error handling
        return api_error("FLOW_NOT_FOUND", "Selected flow was not found", 404, "process_id")

    # Get the task definition row desired by using the operation selected (taskedf id fk) from the agent process row
    taskdef = taskdef_service.get_taskdef_by_id(process.Operation_Selected)
    if not taskdef: # Error handling
        return api_error("TASKDEF_NOT_FOUND", "Flow task definition is missing", 404)

    # Retrive the files the user uploaded from the HTML element                 
    uploaded_files = request.files.getlist("uploaded_file")
    if not uploaded_files: # Error handling
        return api_error("FILES_REQUIRED", "Upload at least one file", 422, "uploaded_file")

    # Create a temp files list 
    temp_files = []

    # Loop the uploaded files, and add them into the temp files list
    for file in uploaded_files:
        if not file or not file.filename:
            continue

        # Get the extension of the file
        extension = os.path.splitext(file.filename)[1]

        # Create a temporary file path variable 
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=extension)

        # Then write data into the file, and close
        temp.write(file.read())
        temp.flush()
        temp.close()

        # Append list with file path and filename
        temp_files.append({"path": temp.name, "name": file.filename})


    # After the temp files array has been populated from the user uploaded files, begin the flow execution
    socketio.start_background_task(
        target = flow_runtime.run_flow,

        # run_flow's needed parameters (not the socketio.start_background_task())
        process_id = process_id,
        taskdef_id = taskdef.TaskDef_ID,
        file_path = temp_files,
        socketio = socketio,
    )

    # Return the values as JSON to be sent back to the frontend (to display the information)
    return jsonify({       
        "status": "started",
        "process_id": process_id,
        "agent_name": process.Agent_Name,
        "message": f"Running '{process.Agent_Name}'..."
    })

########################################################################################################################################


# FLOW SELECTION PAGE 
@app.route("/flow_selection") 
def flow_selection_page():

    # Get all the task defs from the db by calling the service layer 
    taskdefs = taskdef_service.list_taskdefs()

    # Map the task def ID to its row object (used to fetch the desired task def instantly by looking up its id and associated value)
    taskdef_dict = {t.TaskDef_ID: t for t in taskdefs}

    # Extract status messages from the URL to trigger UI toast notifications after a redirect (the value is assigned from the HTML and import flow logic)
    import_error = request.args.get("import_error")
    import_success = request.args.get("import_success")
    ui_toast = request.args.get("ui_toast")

    # Render the flow_selection_page html and pass the python values into the jinja / js page
    return render_template(
        "flow_selection_page.html",
        processes=process_service.list_processes(),
        taskdef_map=taskdef_dict,
        import_error = import_error,
        import_success = import_success,
        ui_toast = ui_toast
    )

#       |
#       | ... Choose a flow
#       V

# VIEW A SELECTED FLOW
@app.route("/flow_viewer/<int:process_id>", methods=["GET"])
def flow_viewer(process_id):

    # Get the desired proccess row from the table by using its matching id 
    process = process_service.get_process(process_id)

    # Error handling 
    if not process:
        return "Agent Flow not found.", 404 

    # Retreive the stages associated with the task def by using 'operation_selected' (taskdef id fk)
    stages = stage_service.get_stages_for_task(process.Operation_Selected)
    taskdef = taskdef_service.get_taskdef_by_id(process.Operation_Selected)
    can_edit_flow = bool(taskdef and taskdef.isSystemCreated != 1)

    return render_template("flow_viewer_page.html", process=process, stages=stages, can_edit_flow=can_edit_flow)

#       |                                             |                                       |
#       | ... Export a flow (button)                  |  ... Edit a flow (button)             | ... Delete a flow (button)
#       V                                             V                                       V

# Export Flow route
@app.route("/process/<int:process_id>/export")
def export_flow(process_id):
    # Fetch the flow definition from the DB using the service
    flow_payload = flow_exchange.export_flow(process_id)
    if not flow_payload:
        return "Flow not found.", 404

    # Build a safe filename from the agent name — replace any special characters with underscores
    agent_name = (flow_payload["flow"].get("agent_name") or "flow").strip()
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in agent_name)
    filename = f"rainn_flow_{safe_name}_{process_id}.json"

    # Serialise the payload and serve it as a downloadable JSON file
    data = json.dumps(flow_payload, indent=2)
    return send_file(
        io.BytesIO(data.encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name=filename
    )


# EDIT FLOW SECTION ################
@app.route("/flow_builder/edit/<int:flow_id>", methods=["GET", "POST"])
def flow_builder_edit_page(flow_id):

    # Get the flow by using the flow_id (from HTML element)
    flow = process_service.get_process(flow_id)

    if not flow:
        return "Flow not found.", 404
    
    # Then get the task def by the agent process.operation selected attribute
    taskdef = taskdef_service.get_taskdef_by_id(flow.Operation_Selected)

    # If the taskdef is not a value or is system created...
    if not taskdef:
        return "Flow definition not found.", 404
    if taskdef.isSystemCreated == 1:
        return "System-created plans cannot be edited.", 403
    

    # The form retreivalw when user saves the edits
    if request.method == "POST":

        # HTML Elements retreival
        agent_name = request.form.get("agent_name")
        agent_priming = request.form.get("agent_priming")
        ai_model = request.form.get("ai_model")

        stage_names = request.form.getlist("stage_name[]")
        stage_descs = request.form.getlist("stage_desc[]")

        # normalise the stages
        edited_stages = normalize_stages(stage_names, stage_descs)

        # If there is no stages
        if not edited_stages:
            return render_template(
                "edit_flow.html",
                flow_id=flow_id,
                agent_name=agent_name,
                agent_priming=agent_priming,
                ai_model=ai_model,
                edit_stages=stage_rows_for_form(stage_names, stage_descs),
                validation_error="Add at least one valid stage before saving."
            ), 422

        # Assign the flow object attributes with the updated values 
        flow.Agent_Name = agent_name
        flow.Agent_Priming = agent_priming
        flow.AI_Model = ai_model

        # Then call the service layer to update in the DB
        process_service.update_process(flow)

        # For cleanup, delete the stages pre-edit of the taskdef
        stage_service.delete_stages_for_task(flow.Operation_Selected)
        
        # Then while looping the editd_stages list...
        for stage_name, stage_desc in edited_stages:

            # Add the new stages
            stage_service.create_stage(flow.Operation_Selected, stage_name, stage_desc)

        return redirect(url_for("flow_selection_page", ui_toast="edit_success"))

    # Get stages 
    stages = stage_service.get_stages_for_task(flow.Operation_Selected)
    edit_stages = []
    for stage in stages:
        edit_stages.append((stage.TaskStageDef_Type, stage.TaskStageDef_Description))

    return render_template(
        "edit_flow.html",
        flow_id=flow_id,
        agent_name=flow.Agent_Name,
        agent_priming=flow.Agent_Priming,
        ai_model=flow.AI_Model,
        edit_stages=edit_stages
    )


# DELETE A FLOW
@app.route("/delete_flow/<int:flow_id>", methods=["POST", "GET"]) 
def delete_flow(flow_id):

    # Call service layer to delete the desired process row
    process_service.delete_process(flow_id)

    return redirect(url_for("flow_selection_page", ui_toast="delete_success"))



########################################################################################################################################


################### CREATE FLOW SECTION ################

@app.route("/flow_builder", methods=["GET", "POST"])
def flow_builder_page():

    # For template load generation by selection, it is needed to put the flow templates in a list and stages in a dict
    template_taskdefs = []
    template_stage_dict = {}

    # Looping...
    for taskdef in taskdef_service.list_taskdefs():
        # If taskdef has this attribute to 1, ignore it
        if taskdef.isSystemCreated != 1:
            continue
        
        # Else put the tempalte taskdefs in the list...
        template_taskdefs.append(taskdef)

        # While adding the stages for the taskdef in the stages dict.. carrying the key of task def id with its values "name" and "desc"
        template_stage_dict[str(taskdef.TaskDef_ID)] = [
            {
                "name": stage.TaskStageDef_Type,
                "desc": stage.TaskStageDef_Description
            }
            for stage in stage_service.get_stages_for_task(taskdef.TaskDef_ID)
        ]

    # form handling
    if request.method == "POST":
        agent_name = (request.form.get("agent_name") or "").strip()
        agent_priming = request.form.get("agent_priming")
        ai_model = request.form.get("ai_model")
        selected_template_id = request.form.get("template_taskdef_id", type=int)

        stage_names = request.form.getlist("stage_name[]")
        stage_descs = request.form.getlist("stage_desc[]")
        edited_stages = normalize_stages(stage_names, stage_descs)

        selected_template = None

        # if the user selects a flow id...
        if selected_template_id:
            # get the selected flow details
            selected_template = taskdef_service.get_taskdef_by_id(selected_template_id)

            # if the selected template is not system created
            if selected_template and selected_template.isSystemCreated != 1:
                selected_template = None

        # If no manual stages were entered...
        if not edited_stages and selected_template:
            edited_stages = [
                (stage.TaskStageDef_Type, stage.TaskStageDef_Description)
                for stage in stage_service.get_stages_for_task(selected_template_id)
            ]
        
        # If there is no stages apparent
        if not edited_stages:
            return render_template(
                "create_flow.html",
                agent_name=agent_name,
                agent_priming=agent_priming,
                ai_model=ai_model,
                selected_template_id=selected_template_id,
                template_taskdefs=template_taskdefs,
                template_stage_map=template_stage_dict,
                edit_stages=stage_rows_for_form(stage_names, stage_descs),
                validation_error="Add at least one valid stage before saving."
            ), 422

        task_description = "Custom plan created by user."
        if selected_template:
            task_description = f"Custom plan derived from template: {selected_template.TaskDef_Name}."

        # Auto-deduplicate names to avoid UNIQUE constraint errors:
        # "Name", "Name (1)", "Name (2)", ...
        resolved_agent_name = next_available_taskdef_name(agent_name)

        # create a new taskdef 
        taskdef_id = taskdef_service.create_taskdef(resolved_agent_name, task_description)

        # create the stages associated with the taskdef
        for stage_name, stage_desc in edited_stages:
            stage_service.create_stage(taskdef_id, stage_name, stage_desc)

        # Then create the flow including all details
        process_service.create_process(
            user_id=1,
            agent_name=resolved_agent_name,
            agent_priming=agent_priming,
            taskdef_id=taskdef_id,
            ai_model=ai_model
        )

        return redirect(url_for("flow_selection_page", ui_toast="create_success"))

    starter_stages = [
        ("input", "Normalise uploaded files into plain text for the workflow."),
        ("extract", "Extract the key points."),
        ("output", "Present the points to the user.")
    ]

    return render_template(
        "create_flow.html",
        agent_name="",
        agent_priming="",
        ai_model="",
        selected_template_id="",
        template_taskdefs=template_taskdefs,
        template_stage_map=template_stage_dict,
        edit_stages=starter_stages
    )


########################################################################################################################################


# FLOW IMPORT ACTION (heading)
@app.route("/flow/import", methods=["POST"])
def flow_import():

    # Get the flow file uploaded from the page and assign it
    uploaded_flow = request.files.get("flow_file")

    # Convert the uploaded file into a JSON text string (or empty if there is not file)
    payload_raw = uploaded_flow.read().decode("utf-8", errors="ignore") if uploaded_flow and uploaded_flow.filename else ""

    # If the payload is not None and fits the character limit... proceed with this condition
    if payload_raw.strip() and len(payload_raw) <= 5000:
        try:
            # Parse the json text (the flow) into a Python object
            payload = json.loads(payload_raw)

            # If the flow validation is successful
            if flow_exchange.validate_flow_payload(payload)[0]:
                # Import the flow
                flow_exchange.import_flow(payload)
            else:
                # Else do not import the flow and return an import error (setting to 1 to activate the pop up)
                return redirect(url_for("flow_selection_page", import_error=1)) 

        # When an exception occurs
        except Exception:
            return redirect(url_for("flow_selection_page", import_error=1))
    # Else, reject the condition
    else:
        return redirect(url_for("flow_selection_page", import_error=1))
    
    return redirect(url_for("flow_selection_page", import_success=1))



########################################################################################################################################


# Page showing all the past flow instances
@app.route("/flow_history") 
def flow_history_page():
    
    # list all the instances in the session using the service layer
    runs = task_instance.list_task_instances()
    return render_template("flow_history_temp.html", runs=runs)

#       |                                               |
#       | ... Select an instance row                    | ... Delete an instance (button)
#       V                                               V

# Specific flow instance details
@app.route("/flow_result/<int:run_id>") 
def past_flow_result_page(run_id):

    # Use service layer to get the desired task instance
    selected_run = task_instance.get_task_instance(run_id)

    # If the selected run is not a value...
    if not selected_run:
        return  "Run not found.", 404
    
    # Use service layer to get the desired instance stages for the task instance
    instance_stages = task_stage_instance.get_stages_for_task_instance(run_id)

    # Assign default values to var "output_text" and "output_type"
    output_text = ""
    output_type = "text"

    # If instance stages has a value...
    if instance_stages:
        
        # Assign the last stage as a variable
        last_stage = instance_stages[-1]

        # Get the artifact path from the attribute of last_stage row
        artifact_path = last_stage.Output_Artifact_Path

        # If there is an artifact path and it exists
        if artifact_path and os.path.exists(artifact_path):
            with open(artifact_path, "r", encoding="utf-8") as f:
                # Read the output artifact file and assign it as a variable
                output_text = f.read()

            # Get the extension of the file and return it to the frontend to determine the correct render type of the output visual
            extension = os.path.splitext(artifact_path)[1].lstrip(".")
            output_type = extension if extension in ("svg", "csv", "json") else "text"
        
    
    return render_template("flow_past_results_page.html", selected_run=selected_run, instance_stages=instance_stages,
                           output_text=output_text, output_type=output_type)

#       |
#       | ... Specific stage instance download link (and for the output as well in the chat)
#       V

### Download the stage artifacts #############
@app.route("/download/<int:run_id>/<filename>")
def download_stage_artifact(run_id, filename):

    # Get the folder of the desired artifact stage
    folder = os.path.join("agent_runs", str(run_id), "artifacts")

    return send_file(os.path.join(folder, filename), as_attachment=True)




# DELETE A TASKINSTANCE 
@app.route("/delete_run/<int:task_instance_id>", methods=["POST"]) 
def delete_run(task_instance_id):

    # run folder path for this task instance
    run_folder = os.path.join("agent_runs", str(task_instance_id))  

    # Delete the numbered run folder 
    shutil.rmtree(run_folder, ignore_errors=True) 

    # Call service layer to delete the desired task stage instance row
    task_stage_instance.delete_for_task_instance(task_instance_id)

    # Call the service layer to delete the desired task stage instance
    task_instance.hard_delete(task_instance_id)

    return redirect(url_for("flow_selection_page"))

########################################################################################################################################




###################################

if __name__ == "__main__":
    socketio.run(app)
