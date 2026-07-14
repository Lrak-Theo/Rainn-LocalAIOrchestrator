from backend.dao.task_def_dao import TaskDefDAO
from backend.model.task_def import TaskDef

class TaskDefService:

    def __init__(self):
        """ Initializes DAO instance for TaskDef operations. """
        self.taskdef_dao = TaskDefDAO()

    # Create a task defenition using the TaskDef class and DAO together
    def create_taskdef(self, name, description, is_system_created=0):
        """ Creates a new TaskDef (agent type). """
        new_task = TaskDef(None, name, description, is_system_created)
        created = self.taskdef_dao.add_TaskDef(new_task)
        return created.TaskDef_ID

    # Retreive the task def by matching id
    def get_taskdef_by_id(self, taskdef_id):
        """ Retrieves a TaskDef by its ID. """
        return self.taskdef_dao.get_TaskDef_by_id(taskdef_id)

    # List all the task defs in the database
    def list_taskdefs(self):
        """ Returns all TaskDefs in the system. """
        return self.taskdef_dao.get_all_TaskDefs()

    # Update the selected taskdef (using id) by using the TaskDef class and DAO
    def update_taskdef(self, taskdef_id, name, description):
        """ Updates an existing TaskDef entry. """
        updated_task = TaskDef(taskdef_id, name, description)
        return self.taskdef_dao.update_TaskDef(updated_task)

    # Delete the taskdef by id 
    def delete_taskdef(self, taskdef_id):
        """ Deletes a TaskDef entry. """
        return self.taskdef_dao.delete_TaskDef(taskdef_id)

    def close(self):
        """ Closes the underlying DAO connection. """
        self.taskdef_dao.close_connection()
