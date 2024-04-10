class EffectNotBuiltError(Exception):
    """Raised when an effect.run() method is called before effect.build()."""

    pass
