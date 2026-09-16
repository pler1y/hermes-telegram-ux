"""Hermes Telegram UX — Catalog-safe entry point (no Hermes imports)."""


def register(ctx):
    from .catalog.adapter import HermesCatalogAdapter

    adapter = HermesCatalogAdapter(ctx)
    adapter.register()
