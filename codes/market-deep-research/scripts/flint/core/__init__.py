import math


def js_round(x: float) -> int:
    """Match JS Math.round: rounds half-values toward +infinity."""
    if isinstance(x, bool):
        return int(x)
    if x is None:
        return 0
    return math.floor(x + 0.5)
