class TaskStageDef:
    """ Represents a stage or step definition linked to a Task Definition. """

    def __init__(self, TaskStageDef_ID, TaskDef_ID_FK, TaskStageDef_Type, TaskStageDef_Description):
        """ Initializes TaskStageDef attributes. """
        self.TaskStageDef_ID = TaskStageDef_ID
        self.TaskDef_ID_FK = TaskDef_ID_FK
        self.TaskStageDef_Type = TaskStageDef_Type # The label / title of the stage
        self.TaskStageDef_Description = TaskStageDef_Description # The description of the stage
        
