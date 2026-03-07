import torch
import torch.nn as nn

class TinyGPT(nn.Module):
    def __init__(self, vocab_size, embed_dim=64, block_size=128, num_heads=4, num_layers=2, dropout=0.1):
        super().__init__()
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.pos_embed = nn.Parameter(torch.zeros(1, block_size, embed_dim))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            batch_first=True  # Fixes the nested tensor warning
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.ln = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, vocab_size)

    def forward(self, x):
        B, T = x.shape
        tok = self.token_embed(x)
        pos = self.pos_embed[:, :T, :]
        x = tok + pos
        x = self.transformer(x)
        x = self.ln(x)
        logits = self.head(x)
        return logits
