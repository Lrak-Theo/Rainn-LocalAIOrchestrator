class AgentProcess:

    def __init__(self, Process_ID, User_ID, Agent_Name, Agent_Priming, AI_Model,
                 Operation_Selected, Created_At):
        
        self.Process_ID = Process_ID
        self.User_ID = User_ID # User_ID is redundant but kept to minimise refactoring of DAO's
        self.Agent_Name = Agent_Name
        self.Agent_Priming = Agent_Priming
        self.AI_Model = AI_Model
        self.Operation_Selected = Operation_Selected # [ Operation Selected ] == TaskDefID (Foreign Key)
        self.Created_At = Created_At # Date