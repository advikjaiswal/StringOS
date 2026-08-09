import torch
import torch.nn as nn


class TinyGPT(nn.Module):
    """Small causal Transformer used by the experimental local planner.

    This model is intentionally kept separate from the default StringOS runtime.
    The causal mask is important: without it, training positions can attend to
    future tokens and next-token evaluation becomes invalid.
    """

    def __init__(self, vocab_size, embed_dim=64, block_size=32, num_heads=4, num_layers=2):
        super().__init__()
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.position_embed = nn.Embedding(block_size, embed_dim)
        self.blocks = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=embed_dim,
                    nhead=num_heads,
                    dim_feedforward=embed_dim * 4,
                    batch_first=True,
                )
                for _ in range(num_layers)
            ]
        )
        self.ln_f = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, vocab_size)
        self.block_size = block_size

    def forward(self, idx):
        _, sequence_length = idx.shape
        if sequence_length > self.block_size:
            raise ValueError(
                f"Sequence length {sequence_length} exceeds block_size={self.block_size}"
            )

        pos = torch.arange(sequence_length, device=idx.device).unsqueeze(0)
        x = self.token_embed(idx) + self.position_embed(pos)
        causal_mask = torch.triu(
            torch.ones(
                sequence_length,
                sequence_length,
                device=idx.device,
                dtype=torch.bool,
            ),
            diagonal=1,
        )
        for block in self.blocks:
            x = block(x, src_mask=causal_mask)
        return self.head(self.ln_f(x))

    def generate(self, input_ids, max_new_tokens=32, eos_token_id=None):
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
