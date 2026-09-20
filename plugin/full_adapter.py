"""The Full runtime's narrow bridge to native turn context and session routing.

Gateway generations and agent hook turn IDs are separate namespaces. The gateway
copies ContextVars into its worker, so an event can retain its exact UI owner even
when a newer generation has replaced it in the session registry.
"""
from contextvars import ContextVar
from functools import wraps
import logging

logger = logging.getLogger(__name__)


current_turn = ContextVar("hermes_ux_turn_owner", default=None)


def serialized_hook(callback):
    """Keep ownership validation and the following registry mutation atomic."""
    @wraps(callback)
    def wrapped(runtime, *args, **kwargs):
        with runtime.registry._lock:
            return callback(runtime, *args, **kwargs)
    return wrapped


def source_key(source, adapter=None):
    """Conservative intake identity before native session routing is available."""
    platform = getattr(source, "platform", "")
    fields = (getattr(platform, "value", platform),
              *(getattr(source, name, None) for name in
                ("profile", "chat_type", "chat_id", "thread_id", "user_id", "user_id_alt")))
    return (id(adapter) if adapter is not None else None,
            *(str(value or "") for value in fields))


class FullAdapter:
    def __init__(self):
        self._session_keys = {}

    def remember_runner(self, runner, source):
        get_adapter = getattr(runner, "_adapter_for_source", None)
        resolver = getattr(runner, "_session_key_for_source", None)
        adapter = get_adapter(source) if callable(get_adapter) else None
        if adapter is not None and callable(resolver):
            self._session_keys[adapter] = resolver
        return adapter

    def session_key(self, source, adapter):
        resolver = self._session_keys.get(adapter)
        try:
            return resolver(source) if resolver is not None else None
        except Exception as error:
            logger.debug("Native session lookup unavailable (%s); using conservative source identity", type(error).__name__)
            return None

    def clear(self):
        self._session_keys.clear()
