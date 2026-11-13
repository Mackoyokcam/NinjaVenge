"""Persistent top-N high score table stored as JSON."""
import json
import os

from . import config

MAX_ENTRIES = 5


def load(path=None):
    path = path or config.SAVE_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data if isinstance(e, dict) and "score" in e][:MAX_ENTRIES]
    except (OSError, ValueError):
        return []


def is_high_score(score, path=None):
    table = load(path)
    return score > 0 and (len(table) < MAX_ENTRIES or score > table[-1]["score"])


def submit(score, wave, path=None):
    """Insert a score; returns (table, rank) where rank is 0-based or None."""
    path = path or config.SAVE_PATH
    table = load(path)
    entry = {"score": int(score), "wave": int(wave)}
    table.append(entry)
    table.sort(key=lambda e: e["score"], reverse=True)
    table = table[:MAX_ENTRIES]
    rank = next((i for i, e in enumerate(table) if e is entry), None)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(table, f)
    except OSError:
        pass  # high scores are a nicety; never crash the game over them
    return table, rank


def best(path=None):
    table = load(path)
    return table[0]["score"] if table else 0
