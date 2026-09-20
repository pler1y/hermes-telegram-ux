"""User-visible progress notes; no execution, routing or tool-result inspection."""
import json
import re

TOOL = "telegram_ux_update"
SCHEMA = {
    "name": TOOL,
    "description": "Update the Telegram user's single progress card with a short public task update or suggested follow-up requests. Does not execute follow-ups. Omit for simple answers.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Short user-facing task goal."},
            "action": {"type": "string", "description": "What you are doing now."},
            "finding": {"type": "string", "description": "One verified finding; never private reasoning or a guess."},
            "next": {"type": "string", "description": "Next intended step, not a completion claim."},
            "followups": {"type": "array", "maxItems": 3, "items": {"type": "string"},
                          "description": "Up to three short, specific requests the user may choose to send after this task. Never execute them now."},
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
    followups = args.get("followups")
    if isinstance(followups, list):
        note["followups"] = list(dict.fromkeys(
            text for value in followups[:3] if (text := public_text(value, 140)) and not text.startswith("/")))
    return {key: value for key, value in note.items() if value}


def progress_tool(args, **kwargs):
    note = normalize_note(args)
    return json.dumps({"ok": bool(note), "note": note,
                       "message": "Public update recorded when this Telegram turn has a supported route. Continue the task; do not repeat this update as a separate message."}, ensure_ascii=False)


def turn_guidance(prefs):
    parts = ["Telegram UX: follow the user's instructions and language. Native Hermes handles task steering, queues, approvals and /stop."]
    if prefs.get("conversation_style"):
        parts.append("Answer simple questions directly. For larger work, keep progress concise, preserve agreed work, and report results before implementation detail. Do not turn routine work into long plans or unnecessary delegation.")
    if prefs.get("progress"):
        parts.append("For multi-step work, use telegram_ux_update sparingly at meaningful milestones with a short goal/current action, verified findings and the next step. It edits one progress card. Do not use it for a one-line answer. Never expose hidden reasoning, secrets, raw commands, tool outputs, fabricated percentages or unverified completion claims. Avoid repeating a card update in a separate interim message.")
    if prefs.get("followups"):
        parts.append("When useful, include up to three relevant followups in telegram_ux_update near the end. They are optional requests for the user to send, not authorization to perform more work. Omit generic or unnecessary suggestions.")
    parts.append("Deliver the full answer and files through the normal Hermes reply. This plugin does not confirm message delivery or change task execution.")
    return {"context": "\n".join(parts)}
