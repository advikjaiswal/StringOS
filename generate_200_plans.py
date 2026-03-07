import json
import random

templates = [
    {
        "prompt": "Translate the sentence: '{text}' to {language}.",
        "tool": "translate_text",
        "args": ["text", "language"],
        "task": "Translate text",
    },
    {
        "prompt": "Extract keywords from the paragraph: '{text}'",
        "tool": "extract_keywords",
        "args": ["text"],
        "task": "Extract keywords",
    },
    {
        "prompt": "Summarize the following article: '{text}'",
        "tool": "summarize_text",
        "args": ["text"],
        "task": "Summarize text",
    },
    {
        "prompt": "Analyze sentiment of the review: '{text}'",
        "tool": "analyze_sentiment",
        "args": ["text"],
        "task": "Analyze sentiment",
    },
    {
        "prompt": "Classify the topic of this message: '{text}'",
        "tool": "classify_topic",
        "args": ["text"],
        "task": "Classify topic",
    }
]

sample_texts = [
    "AgentOS is the future of AI automation.",
    "GPT-based agents can revolutionize business workflow.",
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning models require careful tuning.",
    "Data privacy is crucial in modern software."
]
languages = ["French", "Spanish", "German", "Japanese", "Chinese"]

def create_plan(template):
    text = random.choice(sample_texts)
    language = random.choice(languages)
    prompt = template["prompt"].format(text=text, language=language)
    args = {k: (text if k == "text" else language) for k in template["args"]}
    completion = {
        "task": template["task"],
        "tool": template["tool"],
        "args": args,
        "subtasks": [],
        "command": f"{template['tool']}({', '.join(json.dumps(v) for v in args.values())})",
        "priority": random.choice(["low", "medium", "high"]),
        "frequency": random.choice(["one-time", "daily", "weekly"])
    }
    return {"prompt": prompt, "completion": json.dumps(completion)}

train_data = [create_plan(random.choice(templates)) for _ in range(200)]

with open("agentos_train_200.json", "w") as f:
    json.dump(train_data, f, indent=2)

print("Generated 200 training samples to agentos_train_200.json") 