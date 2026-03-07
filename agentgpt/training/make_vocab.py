import json
import re
import argparse
from collections import Counter
import os

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, default='general_tasks.txt')
parser.add_argument('--vocab_size', type=int, default=2000)
args = parser.parse_args()

input_file = args.input
max_vocab_size = args.vocab_size
raw_text = ''
if input_file.endswith('.jsonl'):
    with open(input_file, 'r') as f:
        for line in f:
            ex = json.loads(line)
            raw_text += ex.get('prompt', '').lower() + '\n' + ex.get('response', '').lower() + '\n'
else:
    with open(input_file, 'r') as f:
        raw_text = f.read().lower()

def tokenize(text):
    pattern = r'task:|\w+|[^\s\w]'
    return re.findall(pattern, text.lower())

# 1. Required tokens (from file and hardcoded)
required_tokens = set(["ai", "research", "lab"])
common_tasks_path = os.path.join(os.path.dirname(__file__), "common_tasks.txt")
if os.path.exists(common_tasks_path):
    with open(common_tasks_path, "r") as f:
        for line in f:
            for word in tokenize(line.strip().lower()):
                if word:
                    required_tokens.add(word)

# 2. Build vocab: always add required tokens first
vocab = {"<PAD>": 0, "<UNK>": 1}
for word in required_tokens:
    if word not in vocab:
        vocab[word] = len(vocab)

# 3. Fill up with most common tokens from data, skipping any already present
counter = Counter(tokenize(raw_text))
for tok, _ in counter.most_common():
    if len(vocab) >= max_vocab_size:
        break
    if tok not in vocab:
        vocab[tok] = len(vocab)

print(f"📚 Vocab size: {len(vocab)}")
print("Required tokens present:", all(w in vocab for w in ["ai", "research", "lab"]))

with open("vocab.json", "w") as f:
    json.dump(vocab, f, indent=2)
