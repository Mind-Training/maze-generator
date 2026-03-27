"""Public API entry points for mazegen."""

from typing import Optional

from .maze_board import MazeBoardGenerator, MazeGeneratorConfig
from .types import BoardDict


def generate_maze_board(
    word: str,
    size: int,
    locale: str = "es",
    board_id: str = "maze-generated",
    title: Optional[str] = None,
    seed: Optional[int] = None,
) -> BoardDict:
    """Generate a maze board dictionary using a simple function-style API."""
    config = MazeGeneratorConfig(
        size=size,
        word=word,
        locale=locale,
        board_id=board_id,
        title=title or f"Generated Maze - {word.upper()}",
        seed=seed,
    )
    generator = MazeBoardGenerator(config)
    return generator.generate()
