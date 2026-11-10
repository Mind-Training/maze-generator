"""Count complete paths from the marked start that spell the target."""


def count_solutions(cells, edges, start, letters, word, *, budget=30_000):
    """Return 0, 1, 2 (at least two), or None if the search budget runs out."""
    ids = {cell: index for index, cell in enumerate(cells)}
    neighbors = [[] for _ in cells]
    for a, b in edges:
        neighbors[ids[a]].append(ids[b])
        neighbors[ids[b]].append(ids[a])
    glyphs = [letters.get(cell) for cell in cells]
    first = ids[start]
    if glyphs[first] != word[0]:
        return 0
    full = (1 << len(cells)) - 1
    end_mask = sum(1 << i for i, glyph in enumerate(glyphs) if glyph == word[-1])
    solutions = 0
    exhausted = False

    def visit(current, remaining, next_letter):
        nonlocal budget, solutions, exhausted
        budget -= 1
        if budget < 0:
            exhausted = True
            return
        if not remaining:
            solutions += next_letter == len(word)
            return
        if next_letter == len(word):
            return

        # Every unvisited vertex needs two available edges, except for
        # the final vertex, which must carry the last letter.
        available = remaining | (1 << current)
        scan = remaining
        forced_end = False
        while scan:
            bit = scan & -scan
            scan ^= bit
            index = bit.bit_length() - 1
            degree = sum(bool(available & (1 << n)) for n in neighbors[index])
            if degree == 0:
                return
            if degree == 1:
                if forced_end or not end_mask & bit:
                    return
                forced_end = True

        for neighbor in neighbors[current]:
            bit = 1 << neighbor
            if not remaining & bit:
                continue
            glyph = glyphs[neighbor]
            if glyph is not None and glyph != word[next_letter]:
                continue
            visit(neighbor, remaining ^ bit, next_letter + (glyph is not None))
            if solutions >= 2 or exhausted:
                return

    visit(first, full ^ (1 << first), 1)
    return None if exhausted else solutions
