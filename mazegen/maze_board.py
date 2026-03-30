"""Maze board generation core logic."""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .types import BoardDict, Coordinate, Edge
from .utils import normalize_word


@dataclass
class MazeGeneratorConfig:
    size: int
    word: str
    locale: str = "es"
    board_id: str = "maze-generated"
    title: str = "Generated Maze"
    min_extra_edges: int = 6
    max_extra_edges: int = 16
    max_graph_attempts: int = 200
    max_path_attempts_per_graph: int = 80
    seed: Optional[int] = None
    wrap_in_board_key: bool = True


class MazeBoardGenerator:
    def __init__(self, config: MazeGeneratorConfig):
        self.config = config
        self.size = config.size
        self.word = normalize_word(config.word)

        if self.size < 2:
            raise ValueError("size debe ser >= 2")
        if not self.word:
            raise ValueError("word no puede estar vacía")
        if len(self.word) > self.size * self.size:
            raise ValueError(
                f"La palabra tiene {len(self.word)} letras y no cabe en un tablero {self.size}x{self.size}"
            )

        self.random = random.Random(config.seed)
        self.cells: List[Coordinate] = [
            (r, c) for r in range(self.size) for c in range(self.size)
        ]
        self.grid_edges: Set[Edge] = self._all_grid_edges()

    def generate(self) -> BoardDict:
        for _ in range(self.config.max_graph_attempts):
            try:
                base_solution_path = self._build_random_hamiltonian_path()
            except RuntimeError:
                continue

            solution_edges = self._edges_from_path(base_solution_path)
            allowed_edges = self._build_ambiguous_graph(solution_edges)

            final_solution_path = self._find_hamiltonian_path_in_graph(allowed_edges)
            if not final_solution_path:
                continue

            final_solution_path = self._orient_path_for_forced_start(
                allowed_edges, final_solution_path
            )
            if not final_solution_path:
                continue

            if not self._graph_quality_ok(allowed_edges, final_solution_path):
                continue

            letter_positions = self._choose_letter_indices(
                len(final_solution_path), len(self.word)
            )
            letter_by_coord = self._build_letter_map(
                final_solution_path, letter_positions
            )

            return self._build_board_json(
                allowed_edges=allowed_edges,
                solution_path=final_solution_path,
                letter_by_coord=letter_by_coord,
            )

        raise RuntimeError(
            "No se pudo generar un board válido tras muchos intentos. "
            "Prueba con más intentos o relaja las restricciones."
        )

    def _all_grid_edges(self) -> Set[Edge]:
        edges: Set[Edge] = set()
        for r in range(self.size):
            for c in range(self.size):
                current = (r, c)
                for neighbor in self._neighbors(current):
                    if neighbor > current:
                        edges.add(frozenset((current, neighbor)))
        return edges

    def _neighbors(self, cell: Coordinate) -> List[Coordinate]:
        r, c = cell
        result = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                result.append((nr, nc))
        return result

    def _edges_from_path(self, path: List[Coordinate]) -> Set[Edge]:
        return {frozenset((path[i], path[i + 1])) for i in range(len(path) - 1)}

    def _build_random_hamiltonian_path(self) -> List[Coordinate]:
        total = self.size * self.size

        for _ in range(self.config.max_path_attempts_per_graph):
            start = self.random.choice(self.cells)
            visited: Set[Coordinate] = {start}
            path = [start]

            if self._backtrack_grid_path(start, visited, path, total):
                return path

        raise RuntimeError("No se pudo construir solutionPath")

    def _backtrack_grid_path(
        self,
        current: Coordinate,
        visited: Set[Coordinate],
        path: List[Coordinate],
        total: int,
    ) -> bool:
        if len(path) == total:
            return True

        candidates = [n for n in self._neighbors(current) if n not in visited]
        self.random.shuffle(candidates)
        candidates.sort(key=lambda cell: self._unvisited_grid_degree(cell, visited))

        for nxt in candidates:
            visited.add(nxt)
            path.append(nxt)

            if self._unvisited_region_connected_on_grid(visited):
                if self._backtrack_grid_path(nxt, visited, path, total):
                    return True

            path.pop()
            visited.remove(nxt)

        return False

    def _unvisited_grid_degree(self, cell: Coordinate, visited: Set[Coordinate]) -> int:
        return sum(1 for n in self._neighbors(cell) if n not in visited)

    def _unvisited_region_connected_on_grid(self, visited: Set[Coordinate]) -> bool:
        unvisited = [cell for cell in self.cells if cell not in visited]
        if not unvisited:
            return True

        start = unvisited[0]
        stack = [start]
        seen = {start}

        while stack:
            cur = stack.pop()
            for nxt in self._neighbors(cur):
                if nxt not in visited and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)

        return len(seen) == len(unvisited)

    def _build_ambiguous_graph(self, solution_edges: Set[Edge]) -> Set[Edge]:
        """
        Parte del camino solución y añade aristas extra,
        pero luego la solución real se vuelve a calcular sobre el grafo final.
        """
        allowed_edges = set(solution_edges)
        extra_candidates = list(self.grid_edges - solution_edges)
        self.random.shuffle(extra_candidates)

        max_possible = len(extra_candidates)
        min_extra = min(self.config.min_extra_edges, max_possible)
        max_extra = min(self.config.max_extra_edges, max_possible)

        if max_extra < min_extra:
            target_extra = min_extra
        else:
            target_extra = self.random.randint(min_extra, max_extra)

        degrees = self._degree_map(allowed_edges)
        added = 0

        for edge in extra_candidates:
            if added >= target_extra:
                break

            a, b = tuple(edge)

            if degrees[a] >= 3 and degrees[b] >= 3 and self.random.random() < 0.75:
                continue

            if self._both_on_border(a, b) and self.random.random() < 0.55:
                continue

            allowed_edges.add(edge)
            degrees[a] += 1
            degrees[b] += 1
            added += 1

        return allowed_edges

    def _find_hamiltonian_path_in_graph(
        self,
        allowed_edges: Set[Edge],
    ) -> Optional[List[Coordinate]]:
        adjacency = self._adjacency_from_edges(allowed_edges)
        total = len(self.cells)

        starts = list(self.cells)
        self.random.shuffle(starts)
        starts.sort(key=lambda cell: len(adjacency[cell]))

        for start in starts:
            visited: Set[Coordinate] = {start}
            path = [start]

            if self._backtrack_graph_path(adjacency, start, visited, path, total):
                return path

        return None

    def _backtrack_graph_path(
        self,
        adjacency: Dict[Coordinate, Set[Coordinate]],
        current: Coordinate,
        visited: Set[Coordinate],
        path: List[Coordinate],
        total: int,
    ) -> bool:
        if len(path) == total:
            return True

        candidates = [n for n in adjacency[current] if n not in visited]
        self.random.shuffle(candidates)
        candidates.sort(
            key=lambda cell: sum(1 for nb in adjacency[cell] if nb not in visited)
        )

        for nxt in candidates:
            visited.add(nxt)
            path.append(nxt)

            if self._unvisited_region_connected_in_graph(adjacency, visited):
                if self._backtrack_graph_path(adjacency, nxt, visited, path, total):
                    return True

            path.pop()
            visited.remove(nxt)

        return False

    def _unvisited_region_connected_in_graph(
        self,
        adjacency: Dict[Coordinate, Set[Coordinate]],
        visited: Set[Coordinate],
    ) -> bool:
        unvisited = [cell for cell in self.cells if cell not in visited]
        if not unvisited:
            return True

        start = unvisited[0]
        stack = [start]
        seen = {start}

        while stack:
            cur = stack.pop()
            for nxt in adjacency[cur]:
                if nxt not in visited and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)

        return len(seen) == len(unvisited)

    def _degree_map(self, edges: Set[Edge]) -> Dict[Coordinate, int]:
        degrees = {cell: 0 for cell in self.cells}
        for edge in edges:
            a, b = tuple(edge)
            degrees[a] += 1
            degrees[b] += 1
        return degrees

    def _adjacency_from_edges(
        self, edges: Set[Edge]
    ) -> Dict[Coordinate, Set[Coordinate]]:
        adjacency = {cell: set() for cell in self.cells}
        for edge in edges:
            a, b = tuple(edge)
            adjacency[a].add(b)
            adjacency[b].add(a)
        return adjacency

    def _both_on_border(self, a: Coordinate, b: Coordinate) -> bool:
        return self._is_border(a) and self._is_border(b)

    def _is_border(self, cell: Coordinate) -> bool:
        r, c = cell
        return r == 0 or c == 0 or r == self.size - 1 or c == self.size - 1

    def _graph_quality_ok(
        self,
        allowed_edges: Set[Edge],
        solution_path: List[Coordinate],
    ) -> bool:
        degrees = self._degree_map(allowed_edges)
        values = list(degrees.values())
        avg_degree = sum(values) / len(values)

        if avg_degree < 2.10:
            return False
        if avg_degree > 3.35:
            return False

        branching_nodes = sum(1 for d in values if d >= 3)
        if branching_nodes < max(3, self.size - 1):
            return False

        degree_one_nodes = sum(1 for d in values if d == 1)
        if degree_one_nodes < 1:
            return False
        if degree_one_nodes > 2:
            return False

        straightness = self._path_straightness(solution_path)
        if straightness > 0.82:
            return False

        ambiguous_steps = self._count_ambiguous_solution_steps(
            allowed_edges, solution_path
        )
        if ambiguous_steps < max(3, self.size - 1):
            return False

        if not self._is_forced_start_cell(allowed_edges, solution_path, 0):
            return False

        return True

    def _path_straightness(self, path: List[Coordinate]) -> float:
        if len(path) < 3:
            return 1.0

        straight = 0
        total = 0
        for i in range(1, len(path) - 1):
            a = path[i - 1]
            b = path[i]
            c = path[i + 1]

            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - b[0], c[1] - b[1])

            total += 1
            if v1 == v2:
                straight += 1

        return straight / total if total else 1.0

    def _count_ambiguous_solution_steps(
        self,
        allowed_edges: Set[Edge],
        solution_path: List[Coordinate],
    ) -> int:
        adjacency = self._adjacency_from_edges(allowed_edges)
        count = 0

        for i in range(len(solution_path) - 1):
            current = solution_path[i]
            nxt = solution_path[i + 1]

            legal_options = adjacency[current]
            if len(legal_options) >= 2 and nxt in legal_options:
                count += 1

        return count

    def _orient_path_for_forced_start(
        self,
        allowed_edges: Set[Edge],
        solution_path: List[Coordinate],
    ) -> Optional[List[Coordinate]]:
        """
        Asegura que el path empiece en una celda válida para la primera letra:
        una celda con exactamente una salida libre, y esa salida debe ser
        hacia el siguiente paso del path.
        """
        if self._is_forced_start_cell(allowed_edges, solution_path, 0):
            return solution_path

        reversed_path = list(reversed(solution_path))
        if self._is_forced_start_cell(allowed_edges, reversed_path, 0):
            return reversed_path

        return None

    def _is_forced_start_cell(
        self,
        allowed_edges: Set[Edge],
        solution_path: List[Coordinate],
        index: int,
    ) -> bool:
        """
        La celda en solution_path[index] debe tener exactamente una salida libre
        y esa salida debe coincidir con el lado por el que continúa la solución.
        """
        if index < 0 or index >= len(solution_path) - 1:
            return False

        adjacency = self._adjacency_from_edges(allowed_edges)
        current = solution_path[index]
        nxt = solution_path[index + 1]
        legal_options = adjacency[current]

        return len(legal_options) == 1 and nxt in legal_options

    def _choose_letter_indices(self, path_len: int, word_len: int) -> List[int]:
        """
        Reparte letras a lo largo de toda la solución manteniendo orden.

        Reglas importantes:
        - La primera letra SIEMPRE va en el inicio del path (índice 0).
        - La última letra SIEMPRE va al final del path (índice path_len - 1).
          Así, cuando completes la palabra, el board estará al 100% rellenado.
        - Las letras intermedias se distribuyen entre medias con algo de jitter,
          pero sin romper el orden ni dejar la última antes del final.
        """
        if word_len < 1:
            raise ValueError("word_len debe ser >= 1")
        if word_len > path_len:
            raise ValueError("word_len no puede ser mayor que path_len")

        if word_len == 1:
            return [0]

        if word_len == 2:
            return [0, path_len - 1]

        result: List[int] = [0]
        max_index = path_len - 1

        for i in range(1, word_len - 1):
            ideal = round(i * max_index / (word_len - 1))

            left_limit = result[-1] + 1
            right_limit = max_index - ((word_len - 1) - i)

            jitter = self.random.randint(-2, 2)
            candidate = ideal + jitter
            candidate = max(left_limit, min(right_limit, candidate))

            result.append(candidate)

        result.append(max_index)
        return result

    def _build_letter_map(
        self,
        solution_path: List[Coordinate],
        letter_positions: List[int],
    ) -> Dict[Coordinate, str]:
        letter_by_coord = {
            solution_path[idx]: ch for idx, ch in zip(letter_positions, self.word)
        }

        # Caso especial para palabras de una sola letra:
        # el path debe empezar y terminar en celdas con letra.
        if len(self.word) == 1:
            letter_by_coord[solution_path[-1]] = self.word[0]

        return letter_by_coord

    def _build_board_json(
        self,
        allowed_edges: Set[Edge],
        solution_path: List[Coordinate],
        letter_by_coord: Dict[Coordinate, str],
    ) -> BoardDict:
        cells_json: List[List[Dict]] = []

        start_coord = solution_path[0]

        for row in range(self.size):
            row_cells: List[Dict] = []

            for col in range(self.size):
                coord = (row, col)

                walls = {
                    "top": self._has_wall(coord, (-1, 0), allowed_edges),
                    "right": self._has_wall(coord, (0, 1), allowed_edges),
                    "bottom": self._has_wall(coord, (1, 0), allowed_edges),
                    "left": self._has_wall(coord, (0, -1), allowed_edges),
                }

                cell_data = {
                    "row": row,
                    "col": col,
                    "isPlayable": True,
                    "walls": walls,
                }

                if coord in letter_by_coord:
                    cell_data["letter"] = letter_by_coord[coord]

                    if coord == start_coord:
                        cell_data["start"] = True

                row_cells.append(cell_data)

            cells_json.append(row_cells)

        board_content = {
            "metadata": {
                "id": self.config.board_id,
                "title": self.config.title,
                "target": self.word,
                "locale": self.config.locale,
            },
            "dimensions": {
                "rows": self.size,
                "cols": self.size,
            },
            "cells": cells_json,
            "solutionPath": [{"row": r, "col": c} for r, c in solution_path],
        }

        if self.config.wrap_in_board_key:
            return {"board": board_content}

        return board_content

    def _has_wall(
        self,
        coord: Coordinate,
        delta: Coordinate,
        allowed_edges: Set[Edge],
    ) -> bool:
        nr, nc = coord[0] + delta[0], coord[1] + delta[1]
        if not (0 <= nr < self.size and 0 <= nc < self.size):
            return True

        neighbor = (nr, nc)
        return frozenset((coord, neighbor)) not in allowed_edges
