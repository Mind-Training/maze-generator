# mazegen

`mazegen` es una librería Python para generar tableros del juego **maze** de forma automática.

## Instalación

### Con Poetry

```bash
poetry add ../mazegen
```

### Con pip (editable para desarrollo local)

```bash
pip install -e ../mazegen
```

## Uso rápido

```python
from mazegen import MazeGeneratorConfig, MazeBoardGenerator

config = MazeGeneratorConfig(
    size=10,
    word="CHATGPT",
    locale="es",
    board_id="maze-chatgpt-10x10",
    title="Maze - CHATGPT",
    seed=20,
)

generator = MazeBoardGenerator(config)
board = generator.generate()

print(board["board"]["metadata"])
```

## API principal

### `MazeGeneratorConfig`

Dataclass de configuración del generador:

- `size`: tamaño del tablero (`size x size`)
- `word`: palabra objetivo
- `locale`: locale de metadata
- `board_id`: identificador del board
- `title`: título del board
- `min_extra_edges` / `max_extra_edges`: nivel de ambigüedad estructural
- `max_graph_attempts`: intentos máximos de generación de grafo
- `max_path_attempts_per_graph`: intentos de path hamiltoniano por grafo
- `seed`: semilla para reproducibilidad

### `MazeBoardGenerator`

Clase principal para generar tableros:

```python
generator = MazeBoardGenerator(config)
board = generator.generate()
```

### `generate_maze_board(...)`

Función de conveniencia para generar un board sin crear explícitamente la clase:

```python
from mazegen import generate_maze_board

board = generate_maze_board(
    word="TESTING",
    size=6,
    locale="es",
    board_id="maze-TESTING-6x6",
    title="Maze - TESTING",
    seed=20,
)
```

## Compatibilidad con el script anterior

Se mantiene `app.py` como wrapper mínimo para ejecutar una generación local por consola, pero toda la lógica vive ahora en el paquete `mazegen`.

## Publicación

El repositorio incluye un workflow base en `.github/workflows/python-publish.yml` para construir y publicar el paquete cuando se publique un release en GitHub o al ejecutar manualmente el workflow.
