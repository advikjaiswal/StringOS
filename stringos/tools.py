from __future__ import annotations

from pathlib import Path
from typing import Callable


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def summarize_text(text: str, max_chars: int = 180) -> str:
    """Deterministic summarizer for the zero-dependency runtime demo."""
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def write_text(path: str, content: str) -> str:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return str(destination)


def fail_once(fn: Callable[..., str]) -> Callable[..., str]:
    """Wrap a tool to inject one deterministic transient failure for testing."""
    failed = False

    def wrapped(**kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected transient failure")
        return fn(**kwargs)

    return wrapped
