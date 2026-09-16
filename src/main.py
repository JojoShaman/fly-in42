import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from parsing import Parsing  # noqa: E402
from render import rendering  # noqa: E402
from simulation import NoPathFound # noqa: E402
import sys  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) == 2:
        try:
            map_p = sys.argv[1]
        except FileNotFoundError as e:
            print(e)
            sys.exit()
    else:
        map_p = 'maps/hard/01_maze_nightmare.txt'
    try:
        data = Parsing().parse(map_p)
    except Exception as e:
        print(e)
        sys.exit()
    try:
        rendering(data, map_p)
    except KeyboardInterrupt:
        print('\nProgram closed successfully')
    except NoPathFound as e:
        print(e)
