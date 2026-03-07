# tool_agent.py
import ast
import traceback
from memory import memory  # memory integration
from tools import *
from agent_core import Agent  # use Agent as the base class

class ToolUseAgent(Agent):
    async def handle(self, msg):
        sender = msg['from']
        body = msg['body']
        agent_name = self.name

        # Log incoming message
        memory.remember(agent_name, sender, body)

        if body.startswith('code:'):
            code = body[len('code:'):].strip()
            try:
                result = eval(code, globals(), locals())
                memory.remember(agent_name, agent_name, f"Executed code `{code}` -> {result}")
                await self.send('Planner', f"Output of `{code}` is: {result}")
            except Exception as e:
                err = traceback.format_exc()
                memory.remember(agent_name, agent_name, f"Code error `{code}` -> {err}")
                await self.send('Planner', f"Error while executing `{code}`:\n{err}")

        elif body.startswith('tool:'):
            try:
                parsed = ast.literal_eval(body[len('tool:'):].strip())
                tool = parsed['name']
                args = parsed.get('args', [])

                # Optionally inject memory-based context
                if 'recall' in parsed and parsed['recall']:
                    past_msgs = memory.recall(agent_name)
                    args.append(f"MEMORY: {past_msgs}")

                result = self.kernel.get_tool(tool)(*args)
                memory.remember(agent_name, agent_name, f"Tool `{tool}` args={args} -> {result}")
                await self.send('Planner', f"Tool `{tool}` executed. Result: {result}")
            except Exception as e:
                memory.remember(agent_name, agent_name, f"Tool error `{tool}` -> {str(e)}")
                await self.send('Planner', f"Tool execution error: {str(e)}")

        await self.kernel.remove_agent(agent_name)  # Self-destruct after use
