"""Type definitions for mazegen."""

from typing import Any, Dict, FrozenSet, Tuple

Coordinate = Tuple[int, int]
Edge = FrozenSet[Coordinate]
BoardDict = Dict[str, Any]
