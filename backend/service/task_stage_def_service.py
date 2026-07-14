from backend.dao.task_stage_def_dao import TaskStageDefDAO
from backend.model.task_stage_def import TaskStageDef

class TaskStageService:
    """ Provides a service layer dedicated to TaskStageDef management. """

    def __init__(self):
        """ Initializes DAO instance for TaskStageDef operations. """
        self.taskstage_dao = TaskStageDefDAO()

    # Create a new stage using the TaskStageDef class and its DAO
    def create_stage(self, taskdef_id, stage_type, description):
        """ Creates a new stage for a specific TaskDef. """
        new_stage = TaskStageDef(None, taskdef_id, stage_type, description)
        return self.taskstage_dao.add_TaskStageDef(new_stage)

    # Retreive the stages for the task (using its id) 
    def get_stages_for_task(self, taskdef_id):
        """ Retrieves all stages belonging to a specific TaskDef. """
        return self.taskstage_dao.get_TaskStageDefs_for_task(taskdef_id)

    # Retrieve a stage by using its ID
    def get_stage_by_id(self, stage_id):
        """ Retrieves a single stage by TaskStageDef_ID. """
        return self.taskstage_dao.get_TaskStageDef_by_id(stage_id)

    # List all the stages in the table
    def list_all_stages(self):
        """ Returns all TaskStageDef entries in the system. """
        return self.taskstage_dao.get_all_TaskStageDefs()

    # Delete the stage by using its ID
    def delete_stage(self, stage_id):
        """ Deletes a single TaskStageDef. """
        return self.taskstage_dao.delete_TaskStageDef(stage_id)

    # Delete all stages of a task def by using its ID
    def delete_stages_for_task(self, taskdef_id):
        """ Deletes all stages associated with a given TaskDef. """
        return self.taskstage_dao.delete_TaskStageDefs_for_task(taskdef_id)
    
    def close(self):
        """ Closes the underlying DAO connection. """
        self.taskstage_dao.close_connection()
