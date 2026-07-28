"""Two small numeric helpers over a sequence of numbers.

Public synthetic fixture. This file is not part of Cognitive OS and describes no real
system. It exists so that every advisory provider can be handed the same read-only
diagnosis task and be scored by the same verifier.
"""


def running_total(values):
    """Return the cumulative sums of ``values``, one entry per input element."""
    totals = []
    carried = 0.0
    for value in values:
        carried += value
        totals.append(carried)
    return totals


def arithmetic_mean(values):
    """Return the arithmetic mean of ``values``."""
    total = 0.0
    for value in values:
        total += value
    return total / len(values)
