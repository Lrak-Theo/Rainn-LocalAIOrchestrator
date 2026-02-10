# ==========================================
# File: agent_process_service.py
# Updated in iteration: 4
# Author: Karl Concha
#
# #ChatGPT (OpenAI, 2025) – Assisted in renaming service layer to match
# AgentProcess architecture and ensuring business logic separation
# according to FYP Bible guidelines.
# ==========================================

from dao.agent_process_dao import AgentProcessDAO
from model.agent_process import AgentProcess


class AgentProcessService:
    """ Service layer for managing stored Agent Processes. """

    def __init__(self):
        self.dao = AgentProcessDAO()

    def create_process(self, user_id, agent_name, agent_priming, taskdef_id, ai_model):
        """ Creates a new agent process entry in the database. """
        new_process = AgentProcess(
            Process_ID=None,
            User_ID=user_id,
            Agent_Name=agent_name,
            Agent_Priming=agent_priming,
            Operation_Selected=taskdef_id,
            AI_Model=ai_model,
            Created_At=None
        )
        return self.dao.add_AgentProcess(new_process)

    def get_process(self, process_id):
        """ Retrieves a process by ID. """
        return self.dao.get_AgentProcess_by_id(process_id)

    def list_processes(self):
        """ Returns all stored agent processes (newest first). """
        return self.dao.get_all_AgentProcesses()

    def update_process(self, agent_process):
        """ Full update handler. """
        self.dao.update_AgentProcess(agent_process)

    def delete_process(self, process_id):
        """ Deletes a process record. """
        return self.dao.delete_AgentProcess(process_id)
