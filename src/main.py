import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from parsing import Parsing  # noqa: E402
from render import rendering  # noqa: E402
from simulation import NoPathFound # noqa: E402
import sys  # noqa: E402

if __name__ == "__main__":
    try:
        data = Parsing().parse('maps/hard/01_maze_nightmare.txt')
    except Exception as e:
        print(e)
        sys.exit()
    try:
        rendering(data, 'maps/hard/01_maze_nightmare.txt')
    except KeyboardInterrupt:
        print('\nProgram closed successfully')
    except NoPathFound as e:
        print(e)
