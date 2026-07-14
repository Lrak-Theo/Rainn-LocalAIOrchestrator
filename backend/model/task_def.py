class TaskDef:
    """ Represents a Task Definition entity within the Rainn system. """

    def __init__(self, TaskDef_ID, TaskDef_Name, TaskDef_Description, isSystemCreated=0):
        """ Initializes TaskDef attributes. """
        self.TaskDef_ID = TaskDef_ID
        self.TaskDef_Name = TaskDef_Name # Task Def name is mainly used for system seeded flows
        self.TaskDef_Description = TaskDef_Description
        self.isSystemCreated = isSystemCreated #Integration of isSsystemCreated allows for better filtering of system made flows / task defenitions against user created 
