"""Intentional public progress notes; no task control or final-answer rewriting."""
import json
import re

TOOL = "telegram_ux_update"
SCHEMA = {
    "name": TOOL,
    "description": "Update one temporary Telegram status with a concise public task milestone. Omit for simple answers. This tool does not execute tasks or send final answers.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Short user-facing task goal."},
            "action": {"type": "string", "description": "What you are doing now."},
            "finding": {"type": "string", "description": "One verified finding; never private reasoning or a guess."},
            "next": {"type": "string", "description": "Next intended step, not a completion claim."},
        },
        "additionalProperties": False,
    },
}


def public_text(value, limit=180):
    if not isinstance(value, str):
        return ""
    # Plain text only, single line, no bidi/control characters or delivery directives.
    value = re.sub(r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]", " ", value)
    value = " ".join(value.split())
    if re.match(r"(?i)^(?:MEDIA:|NO_REPLY\b|HEARTBEAT_OK\b)", value):
        return ""
    return value[:limit]


def normalize_note(args):
    if not isinstance(args, dict):
        return {}
    note = {key: public_text(args.get(key)) for key in ("goal", "action", "finding", "next")}
    return {key: value for key, value in note.items() if value}


def progress_tool(args, **kwargs):
    note = normalize_note(args)
    return json.dumps({"ok": bool(note), "note": note,
                       "message": "Public update recorded when this Telegram turn has a supported route. Continue the task; do not repeat this update as a separate message."}, ensure_ascii=False)


def turn_guidance(prefs):
    if not prefs.get("progress"):
        return None
    return {"context": (
        "For substantial work in this Telegram turn, telegram_ux_update can briefly describe "
        "the task goal, current action, a verified finding, or an intended next step. "
        "Use it sparingly when observable tool events alone do not explain the task. "
        "Write a concise public milestone, not reasoning, raw commands, secrets, percentages, "
        "or unverified success. Findings must be supported by actual results; intentions are not completed work. "
        "The plugin renders one temporary status, so do not repeat its update as a separate interim message. "
        "For a simple answer no progress tool is needed. Deliver the answer and attachments normally."
    )}
