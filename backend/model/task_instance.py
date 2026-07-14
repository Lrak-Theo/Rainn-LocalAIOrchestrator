class TaskInstance:
    """ Represents an instance of a task derived from a Task Definition. """

    def __init__(self, TaskInstance_ID, Process_ID_FK, TaskDef_ID_FK, Status, Run_Folder, Created_At, Updated_At):

        """ Initializes TaskInstance attributes. """
        self.TaskInstance_ID = TaskInstance_ID # Each task instance generates a unique ID
        self.Process_ID_FK = Process_ID_FK
        self.TaskDef_ID_FK = TaskDef_ID_FK
        self.Status = Status
        self.Run_Folder = Run_Folder
        self.Created_At = Created_At
        self.Updated_At = Updated_At

        # Note: TaskInstance reperesents the instance of the agent process (not the taskdef alone)
