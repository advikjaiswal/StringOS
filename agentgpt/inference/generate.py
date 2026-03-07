# agentgpt/inference/generate.py

import torch
import sentencepiece as spm
from agentgpt.model.tinygpt import TinyGPT
import numpy as np
import os
from agentgpt.training.config import config  # <-- Add this import
import torch.nn.functional as F  # Add for softmax

# === Load checkpoint (model + tokenizer path) ===
checkpoint_path = "model_general_sp.pth"
checkpoint = torch.load(checkpoint_path, map_location="cpu")
tokenizer_path = checkpoint['tokenizer_model_path']
block_size = checkpoint.get('block_size', config["block_size"])  # Use config default if not in checkpoint

# === Load SentencePiece model ===
sp = spm.SentencePieceProcessor()
sp.load(tokenizer_path)
vocab_size = sp.get_piece_size()

# === Model hyperparameters (match training config) ===
embed_dim = config["embed_dim"]
num_heads = config["num_heads"]
num_layers = config["num_layers"]
# block_size already set above

# === Load model ===
model = TinyGPT(vocab_size, embed_dim, block_size, num_heads, num_layers)
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

# === Prompt for testing (from train.txt) ===
# To test with a custom prompt, set it here:
custom_prompt = '{"goal": "Start a YouTube channel about AI tools", "plan":'
use_custom_prompt = True  # Set to False to use <START>

if use_custom_prompt:
    prompt = custom_prompt
else:
    prompt = '<START>'
input_ids = sp.encode(prompt, out_type=int)
x = torch.tensor([input_ids], dtype=torch.long)

# === Generate until <END> token ===
max_new_tokens = 128
end_token_id = sp.piece_to_id('<END>')
# Ban tokens: <pad>, <unk>, <s>, </s>, blank '▁'
banned_tokens = ['<pad>', '<unk>', '<s>', '</s>', '▁']
banned_ids = [sp.piece_to_id(tok) for tok in banned_tokens if sp.piece_to_id(tok) != -1]

# === Generation settings ===
temperature = 0.7
use_top_k = True
k = 10
use_top_p = True
p = 0.9

generated_ids = []
for step in range(max_new_tokens):
    # Truncate to last block_size tokens
    if x.shape[1] > block_size:
        x = x[:, -block_size:]
    with torch.no_grad():
        logits = model(x)
        logits = logits[0, -1] / temperature  # Apply temperature
        # Ban <END> as first token
        if step == 0:
            logits[end_token_id] = -float('inf')
        # Ban all banned_ids at every step
        for ban_id in banned_ids:
            logits[ban_id] = -float('inf')
        probs = F.softmax(logits, dim=-1)
        # Top-k sampling
        if use_top_k:
            topk_probs, topk_indices = torch.topk(probs, k)
            probs = torch.zeros_like(probs).scatter(0, topk_indices, topk_probs)
        # Top-p (nucleus) sampling
        if use_top_p:
            sorted_probs, sorted_indices = torch.sort(probs, descending=True)
            cumulative_probs = torch.cumsum(sorted_probs, dim=0)
            cutoff = cumulative_probs > p
            if torch.any(cutoff):
                last_index = torch.where(cutoff)[0][0] + 1
                mask = sorted_indices[last_index:]
                probs[mask] = 0
        probs = probs / probs.sum()  # Renormalize
        next_id = torch.multinomial(probs, num_samples=1).item()
        if step == 0:
            # Print top-5 tokens and their probabilities at step 0
            topk = torch.topk(probs, k=5)
            print("Top 5 token predictions at step 0:")
            print([sp.decode([i]) for i in topk.indices.tolist()])
            print("First sampled token ID:", next_id)
            print("Decoded:", sp.decode([next_id]))
        generated_ids.append(next_id)
        x = torch.cat([x, torch.tensor([[next_id]])], dim=1)
        # Only break if <END> and not first token
        if next_id == end_token_id and step > 0:
            break

output_ids = x[0].tolist()
output_text = sp.decode(output_ids)
print("\n=== Completion ===\n" + output_text)
