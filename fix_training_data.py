import json

INPUT_FILE = 'agentgpt/data/one_example.jsonl'
OUTPUT_FILE = 'agentgpt/data/train.txt'

with open(INPUT_FILE, 'r') as f:
    data = json.load(f)
    entry = data[0]
    prompt = entry['prompt'].strip()
    completion = entry['completion'].strip()
    # Remove any existing <START>/<END> if present
    if completion.startswith('<START>'):
        completion = completion[len('<START>'):]
    if completion.endswith('<END>'):
        completion = completion[:-len('<END>')]
    # Wrap with <START> and <END>
    completion = f'<START>{completion}<END>'
    # Write as one line, no extra whitespace
    with open(OUTPUT_FILE, 'w') as out:
        out.write(f'{prompt}{completion}')

print(f'Wrote reformatted data to {OUTPUT_FILE}') 