import sentencepiece as spm
import numpy as np

# Update input path to the new dataset
input_path = 'agentgpt/data/agentos_dataset_10k.txt'
output_path = 'agentgpt/data/train.bin'
tokenizer_path = 'agentgpt/inference/tokenizer/gpt_tokenizer.model'

sp = spm.SentencePieceProcessor()
sp.load(tokenizer_path)
vocab_size = sp.get_piece_size()
print(f"[PREPARE_DATA] Tokenizer vocab size: {vocab_size}")

all_tokens = []
with open(input_path, 'r') as f:
    content = f.read()
    
# Split by ### to get individual examples
examples = content.split('###')
examples = [ex.strip() for ex in examples if ex.strip()]

for example in examples:
    if example:
        tokens = sp.encode(example, out_type=int)
        all_tokens.extend(tokens + [sp.eos_id()])

print(f"[PREPARE_DATA] Sample token IDs: {all_tokens[:50]}")
print(f"[PREPARE_DATA] Max token ID: {max(all_tokens) if all_tokens else 'N/A'}")

arr = np.array(all_tokens, dtype=np.uint16)
arr.tofile(output_path)
print(f"Wrote {len(arr)} tokens to {output_path}") 