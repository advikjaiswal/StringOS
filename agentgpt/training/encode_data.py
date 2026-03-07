import re
import json
import pickle
import os

# === Load vocab ===
with open("vocab.json", "r") as f:
    vocab = json.load(f)

inv_vocab = {tok: int(idx) for tok, idx in vocab.items()}
unk_token = inv_vocab.get("<UNK>", 1)

# === Load your general training data ===
if os.path.exists("general_tasks.jsonl"):
    lines = []
    with open("general_tasks.jsonl", "r") as f:
        for line in f:
            item = json.loads(line)
            lines.append(item["prompt"])
            lines.append(item["response"])
    raw_text = "\n".join(lines)
else:
    with open("general_tasks.txt", "r") as f:
        raw_text = f.read()

# === Simple tokenizer ===
def tokenize(text):
    return re.findall(r'\w+|[^\s\w]', text)

# === Encode ===
tokens = tokenize(raw_text)
encoded = [vocab.get(tok, unk_token) for tok in tokens]

print(f"🔢 Encoded {len(tokens)} tokens.")

# === Save ===
with open("train_tokens.pkl", "wb") as f:
    pickle.dump(encoded, f)
