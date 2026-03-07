import sentencepiece as spm

spm.SentencePieceTrainer.Train(
    input='agent_corpus.txt',
    model_prefix='agent',
    vocab_size=512,  # 🔼 More room for meta tokens + useful BPE chunks
    model_type='bpe',
    character_coverage=0.98,  # 🔽 Lower this just slightly to avoid rare junk chars
    bos_id=1,
    eos_id=2,
    unk_id=0,
    pad_id=-1
)
