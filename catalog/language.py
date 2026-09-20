"""Stateless status-language selection from the current public message only."""
import re


def resolve_language(message, setting="auto"):
    if setting in ("zh", "en"):
        return setting
    if isinstance(message, list):
        message = " ".join(block["text"][:1000] for block in message[:32]
                           if isinstance(block, dict) and block.get("type") == "text"
                           and isinstance(block.get("text"), str))
    text = message[:8000] if isinstance(message, str) else ""
    # Quoted code and paths are task data, not the language of the request.
    text = re.sub(r"```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`]*`", " ", text)
    text = re.sub(r"https?://[^\s<>]+|(?:[A-Za-z]:[\\/]|~/|/)[^\s，。；,;]+", " ", text)
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"
    if re.search(r"[A-Za-z]", text):
        return "en"
    # No history/profile/state lookup: ambiguous numeric or media-only tasks
    # keep the established Chinese fallback. Administrators may fix zh or en.
    return "zh"
