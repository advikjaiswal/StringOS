import sentencepiece as spm

input_file = 'agentgpt/data/train.txt'
model_prefix = 'agentgpt/inference/tokenizer/gpt_tokenizer'
vocab_size = 64
special_tokens_file = 'agentgpt/inference/tokenizer/special_tokens.txt'

with open(special_tokens_file, 'r') as f:
    special_tokens = [line.strip() for line in f if line.strip()]

# Read train.txt, strip leading spaces from each line, and write to a temp file
with open(input_file, 'r') as f:
    lines = [line.lstrip() for line in f]
stripped_file = input_file + '.stripped'
with open(stripped_file, 'w') as f:
    f.writelines(lines)

spm.SentencePieceTrainer.Train(
    input=stripped_file,
    model_prefix=model_prefix,
    vocab_size=vocab_size,
    character_coverage=1.0,
    model_type='bpe',
    pad_id=0,
    unk_id=1,
    bos_id=2,
    eos_id=3,
    user_defined_symbols=special_tokens
)

print(f"Trained SentencePiece tokenizer with vocab_size={vocab_size} and saved to {model_prefix}.model and {model_prefix}.vocab")
