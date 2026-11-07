"""Tolerant number parsing for scraped text ("1,000", "+3", "51.2%", "bo3", "-")."""

import re

_INT = re.compile(r'[+-]?\d[\d,]*')
_FLOAT = re.compile(r'[+-]?\d[\d,]*(?:\.\d+)?')


def to_int(value, default: int = 0) -> int:
    """First whole number found in ``value``; ``default`` when there is none ('-', '', None, 'TBA')."""
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    match = _INT.search(str(value or ''))
    return int(match.group().replace(',', '')) if match else default


def to_float(value, default: float = 0.0) -> float:
    """First number found in ``value`` as float ("1.18", "51.2%", "+4.5%"); ``default`` when there is none."""
    if isinstance(value, (int, float)):
        return float(value)
    match = _FLOAT.search(str(value or ''))
    return float(match.group().replace(',', '')) if match else default
