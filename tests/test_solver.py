import unittest

from mazegen import MazeBoardGenerator, MazeGeneratorConfig
from mazegen.solver import count_solutions


class MazeSolverTests(unittest.TestCase):
    def test_ambiguous_and_unique_boards(self):
        cells = [(r, c) for r in range(3) for c in range(3)]
        edges = {
            frozenset((a, b))
            for a in cells for b in cells
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
        }
        start = (0, 0)
        letters = {start: "A", (2, 2): "B"}
        self.assertEqual(count_solutions(cells, edges, start, letters, "AB"), 2)
        edges.remove(frozenset((start, (1, 0))))
        edges.remove(frozenset(((0, 1), (1, 1))))
        self.assertEqual(count_solutions(cells, edges, start, letters, "AB"), 1)
        self.assertIsNone(count_solutions(cells, edges, start, letters, "AB", budget=1))

    def test_rectangular_board_and_letter_spacing(self):
        config = MazeGeneratorConfig(
            size=None, rows=5, cols=7, word="LABIRINTO", wall_target=4,
            min_walls=4, max_walls=12, max_empty_run=10, seed=0,
        )
        board = MazeBoardGenerator(config).generate()["board"]
        self.assertEqual(board["dimensions"], {"rows": 5, "cols": 7})
        path = [(step["row"], step["col"]) for step in board["solutionPath"]]
        self.assertEqual(len(set(path)), 35)
        self.assertNotIn(path[0], {(0, 0), (0, 6), (4, 0), (4, 6)})
        letters = [board["cells"][r][c].get("letter") for r, c in path]
        self.assertEqual("".join(letter for letter in letters if letter), "LABIRINTO")
        positions = [i for i, letter in enumerate(letters) if letter]
        self.assertLessEqual(max(b - a - 1 for a, b in zip(positions, positions[1:])), 10)


if __name__ == "__main__":
    unittest.main()
