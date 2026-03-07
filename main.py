# main.py

from agentos.recursive_agent import Agent

if __name__ == "__main__":
    prompt = input("🤖 Enter task for Root Agent: ")
    root_agent = Agent(name="RootAgent", task=prompt)
    root_agent.run()
