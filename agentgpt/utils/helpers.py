def flatten_list(nested_list):
    """Flatten a nested list into a single list."""
    return [item for sublist in nested_list for item in sublist]


def chunk_list(lst, chunk_size):
    """Yield successive chunk_size-sized chunks from lst."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size] 