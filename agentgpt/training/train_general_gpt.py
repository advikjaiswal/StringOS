import torch
import torch.nn as nn
import torch.nn.functional as F
import pickle
import os
from tqdm import trange
import sentencepiece as spm
import numpy as np
from agentgpt.model.tinygpt import TinyGPT
from agentgpt.training.config import config

# === Hyperparameters from config ===
embed_dim = config["embed_dim"]
block_size = config["block_size"]
num_heads = config["num_heads"]
num_layers = config["num_layers"]
batch_size = config["batch_size"]
learning_rate = config["learning_rate"]
num_epochs = config["num_epochs"]
validation_split = config.get("validation_split", 0)

def get_tokenizer_and_vocab():
    tokenizer_path = 'agentgpt/tokenizer/spm.model'
    sp = spm.SentencePieceProcessor()
    sp.load(tokenizer_path)
    vocab_size = sp.get_piece_size()
    print(f"[TRAIN] Tokenizer vocab size: {vocab_size}")
    return sp, vocab_size, tokenizer_path

# Load tokenizer and set vocab size
sp, vocab_size, tokenizer_path = get_tokenizer_and_vocab()

# === Load all prompt+completion pairs from train.txt ===
train_path = 'agentgpt/data/train.txt'
print("🚨 Training Data:", open(train_path).read())
with open(train_path, 'r') as f:
    lines = [line.strip() for line in f if line.strip()]
raw_text = '\n'.join(lines)
input_ids = sp.encode(raw_text, out_type=int)
data = np.array(input_ids, dtype=np.int64)
print(f"[TRAIN] Encoded {len(data)} tokens from train.txt")

# === DEBUG: Print input/target tokens and decoded text ===
input_text = "Extract keywords from the paragraph: \"AgentOS is the future of AI automation.\""
target_text = "<START>{\"tool\": \"extract_keywords\"}<END>"
input_ids_debug = sp.encode(input_text, out_type=int)
target_ids_debug = sp.encode(target_text, out_type=int)
print("Input IDs:", input_ids_debug)
print("Target IDs:", target_ids_debug)
print("Decoded Input:", sp.decode(input_ids_debug))
print("Decoded Target:", sp.decode(target_ids_debug))
print("Tokenized Target (str):", sp.encode(target_text, out_type=str))

# === Train/val split (all for training) ===
train_data = data
val_data = data[:block_size]  # dummy val

print(f"🧠 Training on {len(train_data)} tokens.")

# === Safety check for split sizes ===
if len(train_data) < block_size:
    print(f"❌ Not enough tokens in train split for block_size={block_size}. Got {len(train_data)} tokens.")
    exit(1)
if len(val_data) < block_size:
    print(f"❌ Not enough tokens in val split for block_size={block_size}. Got {len(val_data)} tokens.")
    exit(1)

# === Helper: Get batch ===
def get_batch(split):
    data_split = train_data if split == "train" else val_data
    ix = torch.randint(len(data_split) - block_size, (batch_size,))
    x = torch.stack([torch.tensor(data_split[i:i+block_size]) for i in ix])
    y = torch.stack([torch.tensor(data_split[i+1:i+1+block_size]) for i in ix])
    # Print decoded input/target for first batch
    if split == "train":
        print("Decoded input:", sp.decode(x[0].tolist()))
        print("Decoded target:", sp.decode(y[0].tolist()))
    return x, y

# === Training ===
device = "cuda" if torch.cuda.is_available() else "cpu"
model = TinyGPT(vocab_size, embed_dim, block_size, num_heads, num_layers).to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

# === DEBUG: Manual forward pass on single example ===
# (Commented out for automated run)
# with torch.no_grad():
#     x_debug = torch.tensor([input_ids_debug[:block_size]], dtype=torch.long).to(device)
#     y_debug = torch.tensor([target_ids_debug[:block_size]], dtype=torch.long).to(device)
#     logits_debug = model(x_debug)
#     B, T, C = logits_debug.shape
#     loss_debug = F.cross_entropy(logits_debug.view(B*T, C), y_debug.view(B*T))
#     print("[DEBUG] Manual forward pass loss:", loss_debug.item())

eval_interval = 10
for epoch in trange(num_epochs, desc="Training"):
    model.train()
    x, y = get_batch("train")
    x, y = x.to(device), y.to(device)
    logits = model(x)
    # === Fix shape bug: match logits and y sequence length ===
    if logits.size(1) > y.size(1):
        logits = logits[:, :y.size(1), :].contiguous()
    elif logits.size(1) < y.size(1):
        y = y[:, :logits.size(1)]
    B, T, C = logits.shape
    loss = F.cross_entropy(logits.view(-1, C), y.view(-1))

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if epoch % 100 == 0:
        print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
        # Print decoded model output for first batch
        model.eval()
        with torch.no_grad():
            out_logits = model(x)
            out_ids = torch.argmax(out_logits, dim=-1)[0].cpu().tolist()
            print("[DEBUG] Decoded output:", sp.decode(out_ids))
            print("✅ Target:", sp.decode(y[0].cpu().tolist()))
        model.train()

# === Save model and tokenizer path together ===
torch.save({
    'model_state_dict': model.state_dict(),
    'tokenizer_model_path': tokenizer_path,
    'block_size': block_size
}, "model_general_sp.pth")
print("✅ Model and tokenizer path saved to model_general_sp.pth")
