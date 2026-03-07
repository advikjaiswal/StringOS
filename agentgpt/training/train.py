from tokenizer import Tokenizer

# Load raw training data
with open("training_data.txt", "r") as f:
    raw_text = f.read()

# Build vocab and encode data
tokenizer = Tokenizer()
tokenizer.build_vocab(raw_text, vocab_size=256)
encoded = tokenizer.encode(raw_text)

# Save encoded data
import pickle
with open("train_tokens.pkl", "wb") as f:
    pickle.dump(encoded, f)

# Save vocab
tokenizer.save("vocab.json")

print(f"[✅ Done] Tokenized {len(encoded)} tokens.")
