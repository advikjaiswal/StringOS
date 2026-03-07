import sentencepiece as spm
import torch
import os

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'agentgpt/models/model_general_sp.pth'))
checkpoint = torch.load(MODEL_PATH, map_location="cpu")
tokenizer_path = checkpoint['tokenizer_model_path']
sp = spm.SentencePieceProcessor()
sp.load(tokenizer_path)

prompt = "Extract keywords from the paragraph: 'AgentOS is the future of AI automation.'"
tokens = sp.encode(prompt, out_type=str)
print(tokens) 