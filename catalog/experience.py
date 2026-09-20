"""Intentional public progress notes; no task control or final-answer rewriting."""
import json
import re

from .intelligence import safe_label

TOOL = "telegram_ux_update"
SCHEMA = {
    "name": TOOL,
    "description": (
        "For substantial multi-step work, update the temporary Telegram status when entering a meaningful "
        "new stage that tool events cannot explain, such as comparing sources or checking data anomalies. "
        "Search/read events show activity and sources, but not a changed verification purpose; announce that purpose with action. "
        "Prefer a short, concrete action and its current work object. Skip simple answers, repeated status, "
        "and stages already clear from tool activity. This tool does not execute work or send final answers."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "maxLength": 180, "description": "Optional brief purpose; not the user's question and not a progress update by itself."},
            "action": {"type": "string", "maxLength": 180, "description": "Preferred: the specific work happening now and its object, e.g. comparing dates across sources. No reasoning or generic busy text."},
            "finding": {"type": "string", "maxLength": 180, "description": "One fact already supported by actual tool results. The status only accepts facts it can verify from recognized result structures; other findings may be omitted. Never guess or claim success from intention."},
            "next": {"type": "string", "maxLength": 180, "description": "A concrete intended next stage, explicitly not started or completed work. Use only when the changed plan adds useful information."},
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
    return safe_label(value, limit)


def normalize_note(args):
    if not isinstance(args, dict):
        return {}
    note = {key: public_text(args.get(key)) for key in ("goal", "action", "finding", "next")}
    return {key: value for key, value in note.items() if value}


def progress_tool(args, **kwargs):
    note = normalize_note(args)
    return json.dumps({"ok": bool(note), "note": note,
                       "message": (
                           "Public milestone input accepted; this does not confirm display, verify findings, or mark work complete. "
                           "The turn observer may omit duplicates, unsafe or generic text, and findings it cannot match to recognized tool results. "
                           if note else
                           "No usable public milestone was supplied. Continue the task without retrying this update. "
                       ) + "Continue the actual task. Update again only for a meaningful new stage; do not repeat the update as a separate interim message."}, ensure_ascii=False)


def turn_guidance():
    return {"context": (
        "Telegram progress follows the actual work, not the length of the question. "
        "A direct simple answer needs no update. Reassess as work expands: even a short question may require "
        "original evidence, exact values, time zones, or conflicting sources to be checked. "
        "That is verification work: describe its specific stage instead of carrying the simple-answer exemption forward. "
        "For substantial work, make telegram_ux_update available alongside task tools. "
        "If work expands after you initially skipped it, discover telegram_ux_update by name through the host's public tool search; "
        "if deferred, use the returned schema and invocation route. Discovery itself is not a progress update. "
        "Call telegram_ux_update when the verification target or purpose meaningfully changes, before continuing that work. "
        "Examples include cross-source comparison, checking execution conditions, validating data anomalies, "
        "or moving from collecting or computing evidence to assembling the final comparison. "
        "Search/read events show activity, sources and counts; they do not explain a changed verification purpose. "
        "Prefer action: a short clause naming the current work and object, in the task's language. "
        "Name the specific comparison being assembled, not generic 'preparing the answer'. "
        "Skip updates that repeat the request, last milestone, or an already clear tool stage. "
        "If nothing meaningfully changed, do not update. goal alone is not a stage. "
        "finding must be verified by actual tool results; the observer may omit claims outside recognized result structures. "
        "Never disguise an unsupported finding as action. next is intended work, not work already started or completed; "
        "a failed read alone does not prove recovery. "
        "Write public progress, not reasoning or chain-of-thought. Omit raw search queries, commands, code, secrets, URLs and full paths. "
        "Never invent findings, success or percentages. Do not call on a timer, after every tool, or to meet a count or quota. "
        "Do not repeat the status in a separate interim message; continue the actual task and retain the native final answer."
    )}
