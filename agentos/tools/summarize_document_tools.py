def summarize_document(file_path, summary_length):
    with open(file_path, 'r') as f:
        content = f.read()
    summary = content[:200] + '...'
    return {"status": "success", "summary": summary}
