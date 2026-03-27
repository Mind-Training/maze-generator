"""Internal utilities for mazegen."""


def normalize_word(word: str) -> str:
    """Normalize input words by removing spaces and uppercasing letters."""
    return "".join(word.split()).upper()
