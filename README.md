# AgentOS

AgentOS is a framework for creating and running autonomous AI agents. It is designed to act as an operating system for agents, breaking down complex natural language tasks into actionable, structured plans, and executing them using a customized suite of tools.

At its core, AgentOS operates using a completely local, custom-trained transformer model (`TinyGPT`), providing end-to-end control from mission planning to task execution.

##  Key Features

- **Recursive Autonomous Agents**: Agents can intelligently break down high-level missions into sub-tasks and spawn sub-agents to handle them recursively.
- **Custom Local LLM (`TinyGPT`)**: Built from scratch using PyTorch, `TinyGPT` parses user requests and acts as the "brain," outputting structured JSON plans.
- **Centralized Orchestration**: The `AgentKernel` orchestrates the complete flow—managing memory, invoking the planner, and executing tools based on the generated plan.
- **Extensible Tool Registry**: A plug-and-play tool system where agents can run bash commands, scrape the web, send emails, or execute custom Python functions.
- **Memory Management**: Agents maintain short-term memory of context state and a planner memory of past execution plans to dramatically speed up recurrent tasks.

##  System Architecture

The project is broadly divided into two main subsystems:

### 1. `agentos` (The Runtime Engine)
This is the core execution environment where agents live and work.
- **`recursive_agent.py`**: Contains the `Agent` class which recursively spawns `child_agents` if a task requires multiple steps mapped out by the planner.
- **`agent_kernel.py` & `planner_kernel.py`**: The main orchestration layers. They manage context memory, request plans from the local model, and pass those plans to the `PlannerExecutor`.
- **`planner_agent.py`**: Acts as the bridge that formulates the exact prompt containing context and tools to feed into the GPT model for task breakdown.
- **`memory_engine.py`**: Manages reading, writing, and updating JSON-based local memory (`agent_memory.json` / `planner_memory.json`).
- **`tools/` and `tools_general.py`**: Implementations for specific actions the agent can take, such as `web_scraper`, `bash_runner`, or macOS-specific file cleanup operations. These are registered in `tool_registry.json`.

### 2. `agentgpt` (The Intelligence Core)
This subsystem handles the AI and planning capabilities.
- **`model/tinygpt.py`**: A lightweight PyTorch implementation of a Decoder-Only Transformer (similar to GPT). It features token/positional embeddings, multi-head self-attention, and a causal generation loop.
- **`training/train_general_gpt.py`**: The training script that fine-tunes `TinyGPT` on prompt-completion pairs to specifically output structured JSON tool calls instead of conversational text.
- **`tokenizer/spm.model`**: Uses a custom SentencePiece tokenizer for efficient text encoding/decoding.

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- PyTorch
- SentencePiece

*(It is recommended to use the generated `venv` or `venv311` for isolating dependencies).*

### Training the Model
If you want to train `TinyGPT` on new customized tool schemas or prompt-completion pairs:
```bash
python agentgpt/training/train_general_gpt.py
```
This requires `agentgpt/data/train.txt` to be present and populated. The script will save the updated weights as `model_general_sp.pth`.

### Running the Agent Kernel
To test the core `AgentKernel` operating with the planner and executing a hardcoded prompt:
```bash
python agentos/agent_kernel.py
```

### Running the Interactive Agent (Entry Point)
To start the root agent with an interactive prompt:
```bash
python main.py
```
*Prompt Example:* `Enter task for Root Agent: Extract keywords from the phrase "AgentOS is great" and email the result.`

##  Extending AgentOS (Adding New Tools)

You can easily equip AgentOS with new capabilities. 
1. **Write the Tool**: Create your Python function in `agentos/tools.py`.
2. **Register the Schema**: Open `tool_registry.json` and add your function's signature, expected arguments, and module name.
3. **Load the Tool**: Ensure `AgentKernel.load_tools()` registers it with the `PlannerExecutor`.

Next time the `PlannerAgent` processes a task, it will naturally incorporate the new tool into its plan!
