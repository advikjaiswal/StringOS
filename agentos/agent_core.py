import uuid

class Agent:
    def __init__(self, name, task, memory=None, parent_id=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.task = task
        self.memory = memory or []
        self.parent_id = parent_id
        self.children = []

    def think(self):
        print(f"[🧠 {self.name}] Thinking on task: {self.task}")
        # Call GPT, RAG, or any logic here (currently using your GPTWrapper)
        return f"Agent '{self.name}' is working on: {self.task}"

    def spawn_baby(self, baby_name, baby_task):
        baby = Agent(name=baby_name, task=baby_task, parent_id=self.id)
        self.children.append(baby)
        print(f"👶 Spawned baby agent '{baby.name}' for task: {baby.task}")
        return baby

    async def send(self, to, message):
        print(f"[SEND] To: {to} | Message: {message}")
