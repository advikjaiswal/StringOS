import json
import random

TASK_TEMPLATES = [
    ("Extract keywords from the paragraph: \"{text}\"",
     "extract_keywords",
     "Extract keywords"),
    ("Summarize this text: \"{text}\"",
     "summarize_document",
     "Summarize document"),
    ("Translate the sentence to French: \"{text}\"",
     "translate_text",
     "Translate to French"),
    ("Generate hashtags for: \"{text}\"",
     "generate_hashtags",
     "Generate hashtags"),
]

PARAGRAPHS = [
    "AgentOS is the future of AI automation.",
    "OpenAI models can reason over structured data.",
    "The Eiffel Tower is located in Paris.",
    "John sent the quarterly report to marketing.",
    "Learning by building real projects is effective.",
    "YouTube automation can grow your audience passively.",
    "High-quality data improves model generalization.",
    "Running a startup requires focus and rapid iteration.",
]

def generate_entry():
    paragraph = random.choice(PARAGRAPHS)
    template, tool, task = random.choice(TASK_TEMPLATES)
    prompt = template.format(text=paragraph)

    json_plan = {
        "task": task,
        "tool": tool,
        "args": {
            "text": paragraph
        },
        "subtasks": [],
        "command": f"{tool}('{paragraph}')",
        "priority": "medium"
    }

    return {
        "prompt": prompt,
        "completion": f"<START>{json.dumps(json_plan)}<END>"
    }

def generate_dataset(n=1000, out_path="agentgpt/data/train.jsonl"):
    with open(out_path, "w") as f:
        for _ in range(n):
            sample = generate_entry()
            f.write(json.dumps(sample) + "\n")

    print(f"✅ Generated {n} examples to {out_path}")

if __name__ == "__main__":
    generate_dataset(1000) 