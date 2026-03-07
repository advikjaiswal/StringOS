import re
import json
from collections import Counter
import sentencepiece as spm

class Tokenizer:
    def __init__(self, model_path="agentgpt/inference/tokenizer/gpt_tokenizer.model"):
        print(f"[DEBUG] Tokenizer loading model path: {model_path}")
        self.sp = spm.SentencePieceProcessor()
        self.sp.load(model_path)
        self.model_path = model_path

    def vocab_size(self):
        return self.sp.get_piece_size()

    def encode(self, text):
        return self.sp.encode(text, out_type=int)

    def decode(self, token_ids):
        return self.sp.decode(token_ids)

    # The following methods are legacy and not used with SentencePiece
    def build_vocab(self, text, vocab_size=256):
        pass
    def save(self, path):
        pass
    def load(self, path):
        pass

# Standalone encode/decode functions for compatibility

def encode(text, model_path="agentgpt/inference/tokenizer/gpt_tokenizer.model"):
    sp = spm.SentencePieceProcessor()
    sp.load(model_path)
    return sp.encode(text, out_type=int)

def decode(ids, model_path="agentgpt/inference/tokenizer/gpt_tokenizer.model"):
    sp = spm.SentencePieceProcessor()
    sp.load(model_path)
    return sp.decode(ids)
