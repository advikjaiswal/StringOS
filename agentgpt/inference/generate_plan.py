# agentgpt/inference/generate_plan.py

import json
import time
import torch
import sentencepiece as spm
from agentgpt.model.tinygpt import TinyGPT
import numpy as np
import os
import re
import sys

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models/model_general_sp.pth'))
MAX_RETRIES = 3
VALID_KEYS = {"tool", "args"}

def run_model(prompt):
    # This is the previous generate() logic
    checkpoint = torch.load(MODEL_PATH, map_location="cpu")
    tokenizer_path = checkpoint['tokenizer_model_path']
    sp = spm.SentencePieceProcessor()
    sp.load(tokenizer_path)
    vocab_size = sp.get_piece_size()
    block_size = checkpoint.get('block_size', 256)  # Default to 256 if not present
    model = TinyGPT(vocab_size, 64, block_size, 4, 2)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    print("Prompt text:", prompt)
    input_ids = sp.encode(prompt, out_type=int)
    if len(input_ids) > block_size:
        print(f"[WARN] Truncating input from {len(input_ids)} to {block_size} tokens.")
        input_ids = input_ids[:block_size]
    print("Tokenized input (input_ids):", input_ids)
    if not input_ids or len(input_ids) < 2:
        print("[FATAL] Tokenizer returned empty or too short input_ids! Aborting.")
        raise ValueError("Tokenizer returned empty or too short input_ids!")
    x = torch.tensor([input_ids], dtype=torch.long)
    max_new_tokens = 64
    try:
    for _ in range(max_new_tokens):
        with torch.no_grad():
            logits = model(x)
            next_id = torch.argmax(logits[0, -1]).item()
            x = torch.cat([x, torch.tensor([[next_id]])], dim=1)
            if next_id == sp.eos_id():
                break
    output_ids = x[0].tolist()
    output_text = sp.decode(output_ids)
        print("RAW OUTPUT:\n", output_text)
        # --- Post-process: strip prompt/context echoes ---
        output_text = postprocess_model_output(output_text, prompt)
        return output_text
    except Exception as e:
        print("[FATAL] Model generation failed:", e)
        print("Inputs were:", x)
        raise

# Add post-processing function
def postprocess_model_output(output_text, prompt):
    # Remove prompt/context lines from output
    lines = output_text.splitlines()
    filtered = [line for line in lines if line.strip() and line.strip() not in prompt]
    output_text = "\n".join(filtered)
    # Try to extract the first valid JSON array from the output
    match = re.search(r'\[.*?\]', output_text, re.DOTALL)
    if match:
        return match.group(0)
    # Fallback: return the cleaned output
    return output_text

def is_valid_plan(output):
    try:
        plan = json.loads(output)
        if not isinstance(plan, list): return False
        for step in plan:
            if not isinstance(step, dict): return False
            if not VALID_KEYS.issubset(step.keys()): return False
        return True
    except Exception:
        return False

def generate_plan(prompt):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            output = run_model(prompt).strip()
            if output is None or len(output) == 0:
                print("❌ Model returned None or empty output")
                sys.stdout.flush()
            else:
                print("🧠 RAW OUTPUT:", output)
                sys.stdout.flush()
            if is_valid_plan(output):
                return json.loads(output)
            else:
                prompt = refine_prompt(prompt)
        except Exception as e:
            prompt = refine_prompt(prompt)
        time.sleep(1)
    return [{
        "tool": "log_event",
        "args": {
            "message": f"Failed to generate plan for: {prompt}",
            "level": "error"
        }
    }]

def refine_prompt(prompt):
    # Simple refinement: rephrase to be more direct
    if "analyze" in prompt and "email" in prompt:
        return "Analyze the file and email a report."
    return prompt + " (please output a valid plan)"

# CLI main for manual testing
if __name__ == "__main__":
    prompt = input("Prompt: ")
    plan = generate_plan(prompt)
