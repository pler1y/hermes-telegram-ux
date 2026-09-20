"""Per-user, per-chat/topic preferences through the public plugin state API."""
import hashlib
import json
from threading import RLock


CHOICES = {
    "language": ("zh", "en"), "display": ("brief", "detail"),
    "progress": (True, False), "final_summary": (False, True),
    "emoji": (True, False), "wait_hint": (True, False),
    "conversation_style": (True, False), "followups": (True, False),
}
DEFAULTS = {key: values[0] for key, values in CHOICES.items()}


def valid(key, value):
    return any(type(value) is type(option) and value == option for option in CHOICES[key])


class Preferences:
    def __init__(self, ctx):
        self.ctx, self.lock = ctx, RLock()
        self.defaults = dict(DEFAULTS)
        for key in CHOICES:
            value = ctx.get_config(key, DEFAULTS[key])
            if valid(key, value):
                self.defaults[key] = value

    def key(self, route):
        scope = [route.chat_id, route.thread_id, route.owner_id]
        return "prefs:" + hashlib.sha256(json.dumps(scope).encode()).hexdigest()

    def read(self, route=None):
        result = dict(self.defaults)
        if route and route.owner_id:
            try:
                saved = self.ctx.state.get(self.key(route), {})
                if isinstance(saved, dict):
                    result.update({key: value for key, value in saved.items()
                                   if key in CHOICES and valid(key, value)})
            except Exception:
                pass  # A state read failure does not interrupt native chat.
        return result

    def toggle(self, route, key):
        if key not in CHOICES or not route.owner_id:
            raise ValueError("Invalid preference")
        with self.lock:
            current = self.read(route)
            choices = CHOICES[key]
            current[key] = choices[(choices.index(current[key]) + 1) % len(choices)]
            # No global config writes; a failed save is reported by the UI.
            self.ctx.state.set(self.key(route), current)
            return current
