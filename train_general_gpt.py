import torch
import torch.nn as nn
import torch.nn.functional as F
import pickle
import os
from tqdm import trange
import sentencepiece as spm
from agentgpt.model.tinygpt import TinyGPT

# === Hyperparameters ===
embed_dim = 64
block_size = 8  # reduced for small dataset
num_heads = 4
num_layers = 2
batch_size = 4  # reduced for small dataset
learning_rate = 1e-3
num_epochs = 200
eval_interval = 10

# === Load SentencePiece model ===
sp = spm.SentencePieceProcessor()
sp.load("tokenizer/gpt_tokenizer.model")
vocab_size = sp.get_piece_size()
print(f"[DEBUG] Model vocab size: {vocab_size}")

# === Load training tokens ===
with open("train_tokens.pkl", "rb") as f:
    data = pickle.load(f)

# === Train/val split ===
split = int(0.9 * len(data))
train_data = data[:split]
val_data = data[split:]

# === Helper: Get batch ===
def get_batch(split):
    data_split = train_data if split == "train" else val_data
    ix = torch.randint(len(data_split) - block_size, (batch_size,))
    x = torch.stack([torch.tensor(data_split[i:i+block_size]) for i in ix])
    y = torch.stack([torch.tensor(data_split[i+1:i+1+block_size]) for i in ix])
    return x, y

# === Training ===
device = "cuda" if torch.cuda.is_available() else "cpu"
model = TinyGPT(vocab_size, embed_dim, block_size, num_heads, num_layers).to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

for epoch in trange(num_epochs, desc="Training"):
    model.train()
    x, y = get_batch("train")
    x, y = x.to(device), y.to(device)
    logits = model(x)
    B, T, C = logits.shape
    loss = F.cross_entropy(logits.view(B*T, C), y.view(B*T))

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if epoch % eval_interval == 0:
        model.eval()
        with torch.no_grad():
            x_val, y_val = get_batch("val")
            x_val, y_val = x_val.to(device), y_val.to(device)
            val_logits = model(x_val)
            val_loss = F.cross_entropy(val_logits.view(B*T, C), y_val.view(B*T))
        print(f"Epoch {epoch} | Train Loss: {loss.item():.4f} | Val Loss: {val_loss.item():.4f}")

# === Save model and tokenizer path together ===
torch.save({
    'model_state_dict': model.state_dict(),
    'tokenizer_model_path': 'tokenizer/gpt_tokenizer.model'
}, "model_general_sp.pth")
print("✅ Model and tokenizer path saved to model_general_sp.pth") 