from __future__ import annotations

import re
import unicodedata


_CHUNK_RE = re.compile(r"[a-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+", re.IGNORECASE)
_CJK_RE = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff]+$")


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def tokenize(text: str) -> list[str]:
    """Tokenize Chinese with character n-grams and Latin text with words.

    This baseline is deliberately local and deterministic. Character n-grams make
    Chinese search useful without a tokenizer dictionary or a downloaded model.
    """
    tokens: list[str] = []
    for chunk in _CHUNK_RE.findall(normalize_text(text)):
        if _CJK_RE.fullmatch(chunk):
            for n in (1, 2, 3):
                if len(chunk) < n:
                    continue
                tokens.extend(f"c{n}:{chunk[index:index+n]}" for index in range(len(chunk) - n + 1))
        else:
            tokens.append(f"w:{chunk}")
            if len(chunk) >= 4:
                tokens.extend(f"a3:{chunk[index:index+3]}" for index in range(len(chunk) - 2))
    return tokens

