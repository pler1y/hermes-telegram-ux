"""A calm, event-driven Telegram interaction layer for Hermes."""

_runtime = None


def register(ctx):
    global _runtime
    from .compat import verify_core
    verify_core()
    from .runtime import InteractionRuntime

    _runtime = InteractionRuntime(ctx)
    _runtime.install()
