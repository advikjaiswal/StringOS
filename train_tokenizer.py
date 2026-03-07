import sentencepiece as spm
 
spm.SentencePieceTrainer.Train('--input=agentgpt/data/train.txt --model_prefix=agentgpt/inference/tokenizer/gpt_tokenizer --vocab_size=800 --character_coverage=1.0 --model_type=bpe --user_defined_symbols=task,tool,args,command,subtasks,priority,frequency')
print('✅ Tokenizer trained and saved to agentgpt/inference/tokenizer/gpt_tokenizer.model') 