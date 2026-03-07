import os
import sentencepiece as spm
import numpy as np
import json

def main():
    # Path to JSONL data
    jsonl_path = os.path.join("agentgpt", "training", "general_tasks.jsonl")
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"{jsonl_path} not found.")

    # Load new SentencePiece model
    sp = spm.SentencePieceProcessor()
    sp.load("agentgpt/inference/tokenizer/gpt_tokenizer.model")

    # Read and encode all prompt+tasks pairs, enforcing strict format
    all_ids = []
    valid_count = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
            except Exception as e:
                print(f"[WARN] Skipping malformed line {i}: {e}")
                continue
            if not isinstance(entry, dict):
                print(f"[WARN] Skipping non-dict line {i}: {entry}")
                continue
            prompt = entry.get("prompt", None)
            tasks = entry.get("tasks", None)
            if not isinstance(prompt, str) or not prompt.strip():
                print(f"[WARN] Skipping line {i}: missing or invalid 'prompt'")
                continue
            if not isinstance(tasks, list) or not tasks or not all(isinstance(t, str) and t.strip() for t in tasks):
                print(f"[WARN] Skipping line {i}: missing or invalid 'tasks' list")
                continue
            # Join tasks into a string for encoding
            task_str = "\n".join(tasks)
            text = prompt.strip() + "\n" + task_str
            ids = sp.encode(text, out_type=int)
            all_ids.extend(ids + [sp.eos_id()])  # Optionally add EOS after each example
            valid_count += 1

    ids = np.array(all_ids, dtype=np.uint16)
    print(f"[DEBUG] Max token ID: {ids.max() if len(ids) else 'N/A'} | Vocab size: {sp.get_piece_size()} | Total tokens: {len(ids)} | Valid examples: {valid_count}")

    # Save the full data split to train.bin
    with open("agentgpt/models/train.bin", "wb") as f:
        f.write(ids.tobytes())

    print(f"Wrote {len(ids)} tokens to agentgpt/models/train.bin")

if __name__ == "__main__":
    main() 