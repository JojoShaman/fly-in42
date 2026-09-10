from parsing import Parsing
from render import visualizer
import sys

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