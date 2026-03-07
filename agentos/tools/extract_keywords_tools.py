from keybert import KeyBERT

def extract_keywords(text):
    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(text, stop_words='english', top_n=5)
    return {"status": "success", "keywords": [kw[0] for kw in keywords]}
