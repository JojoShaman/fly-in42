import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from parsing import Parsing  # noqa: E402
from render import visualizer  # noqa: E402
import sys  # noqa: E402

if __name__ == "__main__":
    try:
        data = Parsing().parse('maps/easy/01_linear_path.txt')
    except Exception as e:
        print(e)
        sys.exit()
    try:
        visualizer(data, 'maps/easy/01_linear_path.txt')
    except KeyboardInterrupt:
        print('\nProgram closed successfully')
