from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Repository:
    """Immutable repository entity"""
    id: int
    full_name: str
    stars: int

@dataclass(frozen=True)
class SearchDimension:
    """Immutable search dimension"""
    name: str
    values: Tuple[str, ...]
    is_primary: bool = False