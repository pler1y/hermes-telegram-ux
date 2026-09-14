"""Preserve native dispatch observation when UX consumes a Telegram update."""
import logging

logger = logging.getLogger(__name__)


async def stop_after_dispatch(adapter, update, context):
    # ApplicationHandlerStop skips PTB's group-99 observer. Forward the ORIGINAL
    # update once so current core ingress accounting (and platform hooks on older
    # supported cores) see it. Do not increment private counters or forward the
    # synthetic /stop event: the native observer owns auth and its event envelope.
    from telegram.ext import ApplicationHandlerStop
    try:
        await adapter._on_platform_update(update, context)
    except Exception:
        logger.debug("Native dispatch observer unavailable", exc_info=True)
    raise ApplicationHandlerStop
