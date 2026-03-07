import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import torch
import sentencepiece as spm
from agentgpt.model.tinygpt import TinyGPT
import numpy as np
from agentgpt.memory.planner_memory import retrieve_similar, log_task
import argparse
import json
import re

def load_model_and_tokenizer():
    # Load the trained model
    model_path = 'model_general_sp.pth'
    checkpoint = torch.load(model_path, map_location='cpu')
    
    # Load tokenizer
    tokenizer_path = 'agentgpt/inference/tokenizer/gpt_tokenizer.model'
    print(f"[DEBUG] generate_general.py loading model: {tokenizer_path}")
    sp = spm.SentencePieceProcessor()
    sp.load(tokenizer_path)
    
    return checkpoint, sp

def generate_completion(prompt, model, tokenizer, max_new_tokens=200, temperature=0.8, top_k=200):
    # Encode the prompt
    prompt_tokens = tokenizer.encode(prompt, out_type=int)
    x = torch.tensor(prompt_tokens, dtype=torch.long, device='cpu').unsqueeze(0)
    
    print(f"[DEBUG] Token IDs: {prompt_tokens}")
    print(f"[DEBUG] Vocab size: {tokenizer.get_piece_size()}")
    print(f"[DEBUG] Max token in prompt: {max(prompt_tokens) if prompt_tokens else 0}")
    print(f"[DEBUG] Prompt length: {len(prompt_tokens)}")
    
    # Generate completion (only pass supported args)
    with torch.no_grad():
        y = model.generate(x, max_new_tokens)
        completion = tokenizer.decode(y[0].tolist())
    
    return completion

def extract_json_from_output(output):
    try:
        match = re.search(r'\{[^{}]*"task"[^{}]*"frequency"[^{}]*"subtasks"[^{}]*"command"[^{}]*\}', output, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            return None
    except Exception as e:
        print("[JSON EXTRACT ERROR]", e)
        return None

def clean_and_parse_output(output):
    json_candidates = re.findall(r'\{.*?\}', output, re.DOTALL)
    for candidate in json_candidates:
        try:
            obj = json.loads(candidate)
            if all(k in obj for k in ["task", "frequency", "subtasks", "command"]):
                return obj
        except json.JSONDecodeError:
            continue
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', type=str, required=False)
    parser.add_argument('--max_new_tokens', type=int, default=200)
    parser.add_argument('--temperature', type=float, default=0.8)
    parser.add_argument('--top_k', type=int, default=200)
    args = parser.parse_args()
    
    # Use a super explicit prompt with JSON format
    if args.prompt:
        prompt = args.prompt
    else:
        prompt = (
            'You are AgentGPT. Respond with a JSON object like this:\n'
            '{\n'
            '  "task": "organize a weekend hiking trip",\n'
            '  "frequency": "one-time",\n'
            '  "subtasks": ["Choose destination", "Book transport", "Pack gear", "Create itinerary"],\n'
            '  "command": "python hike_planner.py --mode weekend"\n'
            '}\n\n'
            'task: organize a weekend hiking trip'
        )

    # Load model and tokenizer
    checkpoint, tokenizer = load_model_and_tokenizer()
    
    # Print vocab size
    vocab_size = tokenizer.get_piece_size()
    print(f"[INFO] Tokenizer vocab size: {vocab_size}")
    if vocab_size != 404:
        print(f"[ERROR] Vocab size is {vocab_size}, but should be 404. Please retrain or re-export the tokenizer with vocab size 404, or point to the correct tokenizer file.")
        exit(1)
    
    # Create model and load state dict
    model = TinyGPT(vocab_size, 64, 128, 4, 2)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # Generate completion
    print("=== Completion ===")
    for attempt in range(3):
        completion = generate_completion(
            prompt, 
            model, 
            tokenizer, 
            args.max_new_tokens, 
            args.temperature, 
            args.top_k
        )
        
        print(completion)
        
        # Parse JSON from output
        parsed_json = extract_json_from_output(completion)
        if not parsed_json:
            parsed_json = clean_and_parse_output(completion)

        if parsed_json:
            print("\n[PARSED JSON]")
            print(json.dumps(parsed_json, indent=2))
            break
        else:
            print(f"\n[FAILED TO PARSE JSON] (attempt {attempt+1})")
            if attempt == 2:
                print("Raw output:", completion)

if __name__ == '__main__':
    main()
