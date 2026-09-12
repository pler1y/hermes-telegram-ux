"""Own reversible host overrides and handler registration as one transaction."""
from contextlib import contextmanager, suppress
from functools import wraps
import inspect


_MISSING = object()


class Overrides:
    def __init__(self):
        self.records = []

    def set(self, target, name, replacement):
        original = getattr(target, name)
        owned = vars(target).get(name, _MISSING)
        active = [True]
        if callable(replacement):
            if inspect.iscoroutinefunction(replacement):
                @wraps(replacement)
                async def installed(*args, **kwargs):
                    return await (replacement if active[0] else original)(*args, **kwargs)
            else:
                @wraps(replacement)
                def installed(*args, **kwargs):
                    return (replacement if active[0] else original)(*args, **kwargs)
        else:
            installed = replacement
        if callable(installed):
            installed._hermes_interaction_active = active
        setattr(target, name, installed)
        self.records.append((target, name, owned, installed, active))
        return installed

    def rollback(self, checkpoint=0):
        records, self.records = self.records[checkpoint:], self.records[:checkpoint]
        for target, name, owned, installed, active in reversed(records):
            # A later plugin may retain our wrapper through functools.wraps. Leave
            # its override intact, but make our retained layer forward to native.
            active[0] = False
            if getattr(target, name, _MISSING) is installed:
                if owned is _MISSING:
                    delattr(target, name)
                else:
                    setattr(target, name, owned)

    @contextmanager
    def transaction(self):
        checkpoint = len(self.records)
        try:
            yield
        except BaseException:
            self.rollback(checkpoint)
            raise


class Handlers:
    """Track every successful add, including a factory that fails halfway through."""
    def __init__(self, application):
        self.application = application
        self.added = []

    def add_handler(self, handler, group=0):
        self.application.add_handler(handler, group=group)
        self.added.append((handler, group))

    def remove_handler(self, handler, group=0):
        if (handler, group) in self.added:
            self.application.remove_handler(handler, group=group)
            self.added.remove((handler, group))

    def close(self):
        for handler, group in reversed(self.added[:]):
            with suppress(Exception):
                self.remove_handler(handler, group)
