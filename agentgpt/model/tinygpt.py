import torch
import torch.nn as nn

class TinyGPT(nn.Module):
    def __init__(self, vocab_size, embed_dim=64, block_size=32, num_heads=4, num_layers=2):
        super().__init__()
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.position_embed = nn.Embedding(block_size, embed_dim)
        self.blocks = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=embed_dim,
                nhead=num_heads,
                dim_feedforward=embed_dim * 4,
                batch_first=True
            )
            for _ in range(num_layers)
        ])
        self.ln_f = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, vocab_size)
        self.block_size = block_size

    def forward(self, idx):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device).unsqueeze(0)
        tok_emb = self.token_embed(idx)
        pos_emb = self.position_embed(pos)
        x = tok_emb + pos_emb
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.head(x)
        return logits 

    def generate(self, input_ids, max_new_tokens=32, eos_token_id=None):
        # input_ids: (1, T)
        for _ in range(max_new_tokens):
            if input_ids.shape[1] >= self.block_size:
                break
            logits = self(input_ids)
            next_token_logits = logits[:, -1, :]
            next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
            input_ids = torch.cat([input_ids, next_token], dim=1)
            if eos_token_id is not None and next_token.item() == eos_token_id:
                break
        return input_ids 