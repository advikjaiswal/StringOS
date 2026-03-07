import torch
import sentencepiece as spm
import os
from agentgpt.model.tinygpt import TinyGPT
from agentgpt.training.config import config

# Load tokenizer
sp = spm.SentencePieceProcessor()
tokenizer_path = 'agentgpt/inference/tokenizer/gpt_tokenizer.model'
sp.load(tokenizer_path)
vocab_size = config["vocab_size"]
block_size = config["block_size"]

# Model config
embed_dim = config["embed_dim"]
num_heads = config["num_heads"]
num_layers = config["num_layers"]

# Prompt and completion
prompt = 'Extract keywords from the paragraph: "AgentOS is the future of AI automation."'
completion = '{"task": "Extract keywords", "tool": "extract_keywords", "args": {"text": "AgentOS is the future of AI automation."}, "subtasks": [], "command": "extract_keywords(\'AgentOS is the future of AI automation.\')", "priority": "medium"}'

# Tokenize
raw_text = prompt + completion
input_ids = sp.encode(raw_text, out_type=int)
data = torch.tensor(input_ids, dtype=torch.long)

# Model
model = TinyGPT(vocab_size, embed_dim, block_size, num_heads, num_layers)
optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"])

# Overfit loop
for step in range(500):
    # Truncate/pad to block_size
    if len(data) < block_size + 1:
        padded = torch.cat([data, torch.zeros(block_size + 1 - len(data), dtype=torch.long)])
    else:
        padded = data[:block_size + 1]
    x = padded[:block_size].unsqueeze(0)
    y = padded[1:block_size+1].unsqueeze(0)
    logits = model(x)
    B, T, C = logits.shape
    loss = torch.nn.functional.cross_entropy(logits.view(B*T, C), y.view(B*T))
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    if step % 50 == 0:
        print(f"Step {step}: loss = {loss.item():.4f}")
print("✅ Debug overfit complete.") 