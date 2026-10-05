"""Regression coverage for deterministic pairwise selection and pytest collection."""

from __future__ import annotations

from itertools import combinations, product
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.pairwise import select_pairwise_indices

if TYPE_CHECKING:
    from collections.abc import Mapping

pytest_plugins = ["pytester"]


def _coverage(case: Mapping[str, object], names: list[str]) -> set[tuple[object, ...]]:
    """Describe value and pair coverage independently of the optimized selector."""
    return {(name, case[name]) for name in names} | {
        (first, case[first], second, case[second]) for first, second in combinations(names, 2)
    }


@pytest.mark.parametrize("sizes", [(2, 3, 2), (3, 4, 2, 2), (1, 3, 1), (4, 4, 3, 2)])
def test_pairwise_preserves_greedy_selection_and_complete_pair_coverage(sizes: tuple[int, ...]) -> None:
    """Preserve original greedy tie choices while covering all declared interactions."""
    names = [f"option_{index}" for index in range(len(sizes))]
    cases = [dict(zip(names, row)) for row in product(*(range(size) for size in sizes))]
    varying_names = [name for name, size in zip(names, sizes) if size > 1]
    tokens = [_coverage(case, varying_names) for case in cases]
    remaining = list(range(len(cases)))
    uncovered = set().union(*tokens)
    expected: list[int] = []
    while uncovered:
        best = max(remaining, key=lambda index: len(tokens[index] & uncovered))
        expected.append(best)
        uncovered.difference_update(tokens[best])
        remaining.remove(best)
    selected = select_pairwise_indices(cases)
    assert selected == sorted(expected)
    assert set().union(*(tokens[index] for index in selected)) == set().union(*tokens)
    assert selected == select_pairwise_indices(cases)


def test_pairwise_empty_constant_and_unhashable_parameters() -> None:
    """Retain a representative for constant options and support native list values."""
    assert select_pairwise_indices([]) == []
    assert select_pairwise_indices([{"value": [1]}, {"value": [1]}]) == [0]
    assert select_pairwise_indices([{"value": [1]}, {"value": [2]}]) == [0, 1]


def test_pairwise_collection_preserves_ids_indirect_fixtures_and_exhaustive_mode(pytester: pytest.Pytester) -> None:
    """Run the actual hook against direct options and a module-scoped indirect fixture."""
    root = str(Path(__file__).resolve().parents[1])
    pytester.makeconftest(f"""
import sys
sys.path.insert(0, {root!r})
from tests import conftest as suite
suite.PAIRWISE_EFFECT_TESTS = frozenset({{("test_cases.py", "test_cases")}})
pytest_addoption = suite.pytest_addoption
pytest_generate_tests = suite.pytest_generate_tests
""")
    pytester.makepyfile(
        test_cases="""
import pytest
setups = []

@pytest.fixture(scope="module", params=[10, 20], ids=["slow", "fast"])
def speed(request):
    setups.append(request.param)
    return request.param * 2

@pytest.fixture
def input_data(request):
    return "resolved:" + request.param

@pytest.mark.parametrize("input_data", ["one", "two"], indirect=True, ids=["first", "second"])
@pytest.mark.parametrize("direction", ["up", "down", "left"])
def test_cases(input_data, direction, speed):
    assert input_data in ("resolved:one", "resolved:two")
    assert speed in (20, 40)
    assert direction in ("up", "down", "left")

def test_module_fixture_stays_module_scoped():
    assert sorted(setups) == [10, 20]
"""
    )

    def collect(*args: str) -> list[str]:
        result = pytester.runpytest_subprocess("--collect-only", "-q", *args)
        assert result.ret == 0
        return [line for line in result.outlines if line.startswith("test_cases.py::test_cases[")]

    selected = collect()
    assert selected == collect()
    exhaustive = collect("--exhaustive-effect-args")
    assert len(selected) == 6
    assert len(exhaustive) == 12
    assert set(selected) < set(exhaustive)
    assert all(any(label in node for node in selected) for label in ("slow", "fast", "first", "second"))
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=7)
    pytester.runpytest_subprocess("-q", "--exhaustive-effect-args").assert_outcomes(passed=13)
