import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from parsing import Parsing  # noqa: E402
from render import rendering  # noqa: E402
from simulation import NoPathFound # noqa: E402
from pydantic import ValidationError  # noqa: E402
from data import Data  # noqa: 402
import sys  # noqa: E402

RED = '\033[31m'
RESET = '\033[0m'

if __name__ == "__main__":
    if len(sys.argv) == 2:
        map_p = sys.argv[1]
    else:
        map_p = 'maps/droken/05_two_starts.txt'
    try:
        data: Data = Parsing().parse(map_p)
        rendering(data, map_p)
    except ValidationError as e:
        word = 'errors' if len(e.errors()) > 1 else 'error'
        print(f'{RED}{len(e.errors())} {word} occurred while attempting to'
              f' parse {map_p}{RESET}')
        print(f'  {RED}➜{RESET} ', e.errors()[0]['msg'])
        sys.exit()
    except ValueError as e:
        sys.exit()
    except FileNotFoundError as e:
        print(type(e).__name__, ':', e)
        sys.exit()
    except KeyboardInterrupt:
        print('\nProgram closed successfully')
    except NoPathFound as e:
        print(e)
