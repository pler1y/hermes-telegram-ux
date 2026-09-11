"""Conversation-scoped background ownership and acknowledgement classification."""
import re


def owned_children(session_id, records):
    owned={r['subagent_id'] for r in records if r.get('owner_agent_session_id') == session_id}
    while True:
        more={r['subagent_id'] for r in records if r.get('parent_id') in owned}
        if more <= owned:return [r for r in records if r.get('subagent_id') in owned]
        owned |= more


def acknowledgement_only(text):
    if not isinstance(text,str):return False
    plain=re.sub(r'[*_`]', '', text).strip()
    if len(plain)>240 or 'http://' in plain or 'https://' in plain:return False
    if re.fullmatch(r"(?:got it|understood|noted|thanks for the update)[.!]?(?:\s*[—–-]\s*|\s+)?(?:I(?:'ll| will) (?:use|follow|apply|work with) (?:your |the )?(?:updated |new )?(?:request|instructions|requirements)[.!]?)?", plain, re.I):
        return True
    # Constraint restatements can contain bullets; do not treat them as substantive results.
    if re.match(r'^(?:收到[，：:]\s*(?:改为|只看|只讲|只比较|按你)|已调整[：:]|已按.{0,35}调整[：:])',plain):return True
    if re.search(r'\n\s*(?:\d+[.、]|[-•])|以下是结果|结果如下|建议|推荐',plain):return False
    return bool(re.match(r'^(?:收到[，：:。！!]|已调整[：:]|已按.{0,35}调整[：:])',plain))
