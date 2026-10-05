"""Deterministic pairwise selection before pytest creates test items."""

from __future__ import annotations

from collections import defaultdict
from heapq import heappop, heappush
from itertools import combinations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def _key(value: object) -> object:
    """Return a hashable parameter identity, matching pytest's former selector."""
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


def select_pairwise_indices(cases: Sequence[Mapping[str, object]]) -> list[int]:
    """Cover every value and value pair, preserving greedy ties in original case order.

    Track how many uncovered tokens each candidate supplies instead of rescoring
    every candidate's intersection after every selection.
    """
    if not cases:
        return []
    names = sorted(name for name in cases[0] if len({_key(case[name]) for case in cases}) > 1)
    tokens_by_case: list[set[tuple[object, ...]]] = []
    candidates_by_token: dict[tuple[object, ...], list[int]] = defaultdict(list)
    for index, case in enumerate(cases):
        values = {name: _key(case[name]) for name in names}
        tokens: set[tuple[object, ...]] = {("value", name, value) for name, value in values.items()}
        tokens.update(
            ("pair", first, values[first], second, values[second]) for first, second in combinations(names, 2)
        )
        tokens_by_case.append(tokens)
        for token in tokens:
            candidates_by_token[token].append(index)
    # Constant-only tests still need one representative case.
    if not candidates_by_token:
        return [0]
    uncovered = set(candidates_by_token)
    gains = [len(tokens) for tokens in tokens_by_case]
    heap: list[tuple[int, int]] = []
    for index, gain in enumerate(gains):
        heappush(heap, (-gain, index))
    selected: set[int] = set()
    while uncovered:
        negative_gain, index = heappop(heap)
        if index in selected or -negative_gain != gains[index]:
            continue
        selected.add(index)
        covered = tokens_by_case[index] & uncovered
        uncovered.difference_update(covered)
        affected: set[int] = set()
        for token in covered:
            for candidate in candidates_by_token[token]:
                if candidate not in selected:
                    gains[candidate] -= 1
                    affected.add(candidate)
        for candidate in affected:
            heappush(heap, (-gains[candidate], candidate))
    return sorted(selected)
