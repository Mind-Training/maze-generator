"""Backward-compatible script entrypoint for local generation."""

import json

from mazegen import generate_maze_board


if __name__ == "__main__":
    board = generate_maze_board(
        word="TESTING",
        size=6,
        locale="es",
        board_id="maze-TESTING-6x6",
        title="Maze - TESTING",
        seed=20,
    )

    print(json.dumps(board, ensure_ascii=False, indent=2))
