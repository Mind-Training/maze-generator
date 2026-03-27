"""mazegen package public API."""

from .core import generate_maze_board
from .maze_board import MazeBoardGenerator, MazeGeneratorConfig

MazeGenerator = MazeBoardGenerator

__all__ = [
    "MazeGeneratorConfig",
    "MazeBoardGenerator",
    "MazeGenerator",
    "generate_maze_board",
]

__version__ = "0.1.0"
