from agentgpt.model.tinygpt import TinyGPT
import sentencepiece as spm
import torch
import os
from agentgpt.training.config import config

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'model_general_sp.pth'))

checkpoint = torch.load(MODEL_PATH, map_location="cpu")
tokenizer_path = checkpoint['tokenizer_model_path']
sp = spm.SentencePieceProcessor()
sp.load(tokenizer_path)
vocab_size = config["vocab_size"]
block_size = checkpoint.get('block_size', config["block_size"])

model = TinyGPT(vocab_size, config["embed_dim"], block_size, config["num_heads"], config["num_layers"])
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

prompt = "Extract key insights from sales data and send a summary report"
input_ids = sp.encode(prompt, out_type=int)
if len(input_ids) > block_size:
    input_ids = input_ids[:block_size]
x = torch.tensor([input_ids], dtype=torch.long)

max_new_tokens = 64
for _ in range(max_new_tokens):
    if x.shape[1] >= block_size:
        x = x[:, -block_size:]
    with torch.no_grad():
        logits = model(x)
        next_id = torch.argmax(logits[0, -1]).item()
        x = torch.cat([x, torch.tensor([[next_id]])], dim=1)
        if next_id == sp.eos_id():
            break
output_ids = x[0].tolist()
output_text = sp.decode(output_ids)
print("🧠 Output:", output_text) 