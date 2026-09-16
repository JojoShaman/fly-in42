from pydantic import ValidationError
import sys
from data import (
    Connection,
    ConnectionMetadata,
    Data,
    Hub,
    Metadata,
    Type,
)

KEYWORDS = ['nb_drones', 'start_hub', 'hub', 'end_hub', 'connection']

_ZONES = {
    'restricted': Type.restricted,
    'priority': Type.priority,
    'blocked': Type.blocked,
}

RED = '\033[31m'
RESET = '\033[0m'

def _parse_metadata(raw: str) -> Metadata:
    meta = Metadata()
    for token in raw.split():
        key, value = token.split('=')
        if key == 'zone':
            if value in _ZONES:
                meta.zone = _ZONES[value]
        elif key == 'color':
            meta.color = value
        elif key == 'max_drones':
            meta.max_drones = value  #type: ignore
    return meta


def _parse_drones(line: str) -> int:
    nb = line.split(':')[1]
    try:
        ret = int(nb)
    except ValueError as e:
        raise ValueError(f"'nb_drones' {e}")
    if ret <= 0:
        raise ValueError("'nb_drones' should be a positive integer.")
    return ret


def _parse_hub(line: str) -> Hub:
    body = line.split(':')[1]
    segments = [part for part in body.split('[') if part.strip()]
    splited = segments[0].strip().split()
    name = splited[0]
    try:
        x = splited[1]
    except ValueError as e:
        raise ValueError("'x'", e)
    except IndexError:
        raise ValueError("'x' field cannot be empty")
    try:
        y = splited[2]
    except ValueError as e:
        raise ValueError("'x'", e)
    except IndexError:
        raise ValueError("'y' field cannot be empty")
    return Hub(
        name=name,
        x=x,  # type: ignore
        y=y,  # type: ignore
        meta_data=_parse_metadata(segments[1].rstrip(']')),
    )


def _parse_connection(line: str) -> Connection:
    tokens = line.split(':')[1].split()
    name1, name2 = tokens[0].split('-')
    if len(tokens) == 2:
        capacity = int(tokens[1].strip('[]').split('=')[1])
        meta_data = ConnectionMetadata(max_link_capacity=capacity)
    else:
        meta_data = ConnectionMetadata()
    return Connection(name1=name1, name2=name2, meta_data=meta_data)


def _read_lines(file: str) -> list[tuple[str, int]]:
    with open(file, 'r') as f:
        content = f.read()
    return [
        (line, n) for n, line in enumerate(content.splitlines(), start=1)
        if line.strip() and not line.startswith('#')
    ]

def check(file: str) -> tuple[bool, bool]:
    with open(file, 'r') as f:
        content = f.read()
    comments: bool = False
    empty_lines: bool = False
    for line in content.splitlines():
        if not line.strip():
            empty_lines = True
        elif line.startswith('#'):
            comments = True
    return((comments, empty_lines))


class ErrorManagement():
    def __init__(self) -> None:
        self.errors: list[tuple[str, int]] = []
        self.nb_errors: int = 0
    
    def _error_manager(self,
                       seen: dict[str, list[tuple[int, str]]]) -> None:
        lines: list[tuple[int, str]] = []
        for key, hubs in seen.items():
            for line, _ in hubs:
                lines.append((line, key))
        lines.sort()
        self._keyword_errors(lines)
        self._missing_errors(seen)
        self._duplicate_errors(seen)

    def _duplicate_errors(self,
                          seen: dict[str, list[tuple[int, str]]]) -> None:
        hubs: dict[str, list[int]] = {}
        for key in ('start_hub', 'hub', 'end_hub'):
            for line, data in seen.get(key, []):
                name = data.split()[0]
                hubs.setdefault(name, []).append(line)
        for h, dup in hubs.items():
            if len(dup) > 1:
                self.nb_errors += len(dup)
                lines = ', '.join(str(l) for l in dup)
                self.errors.append(
                    (f'  {RED}➜{RESET} "{h}" appears multiple times at: '
                     f'lines {lines}', 0))

    def _keyword_errors(self, lines: list[tuple[int, str]]) -> None:
        last_i = -1
        last_key = ''
        for n, k in lines:
            i = KEYWORDS.index(k)
            if i < last_i:
                self.nb_errors += 1
                self.errors.append(
                    (f'  {RED}➜{RESET} line {n}: "{k}" cannot appear '
                     f'after "{last_key}"', n))
            else:
                last_i = i
                last_key = k

    def _missing_errors(self, seen: dict[str, list[tuple[int, str]]]) -> None:
        for key in ('nb_drones', 'start_hub', 'end_hub'):
            nb: int = 0
            if not key in seen:
                self.errors.append((f'  {RED}➜{RESET} missing "{key}"', 0))
                nb += 1
            elif len(seen[key]) > 1:
                nb += len(seen[key])
                lines = ', '.join(str(n) for n, _ in seen[key])
                self.errors.append(
                    (f'  {RED}➜{RESET} "{key}" declared more than once '
                     f'at lines: {lines}', 0))
            self.nb_errors += nb

    def find_similar(self, wrong_k: str) -> str:
        similar: str = ''
        last_inter: set = set()
        for key in KEYWORDS:
            inter: set = set(wrong_k) & set(key)
            if len(inter) > len(last_inter):
                last_inter = inter
                similar = key
        return similar


class Parsing:
    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.start_hub: Hub | None = None
        self.hub: list[Hub] = []
        self.end_hub: Hub | None = None
        self.connections: list[Connection] = []
        self.total_hubs: list[Hub] = []
        self.handle: ErrorManagement = ErrorManagement()

    def parse(self, file: str) -> Data:
        lines = _read_lines(file)
        seen: dict[str, list[tuple[int, str]]] = {}
        if len(lines) > 0:
            for line, n in lines:
                key, body = line.split(':')
                if key.strip() in KEYWORDS:
                    seen.setdefault(key.strip(), []).append((n, body.strip()))
                else:
                    self.handle.nb_errors += 1
                    self.handle.errors.append(
                        (f"  {RED}➜{RESET} line {n}: keyword '{key}' is"
                        " not valid. Perhaps you meant "
                        f"'{self.handle.find_similar(key)}'?", n))
            self.handle._error_manager(seen)
            if self.handle.errors:
                self._report(self.handle, file)
                sys.exit()
        else:
            comments, empty = check(file)
            if comments or empty:
                status: str = ''
                if comments and empty:
                    status = 'comments and empty lines'
                else:
                    status = 'comments' if comments else 'empty lines'
                self.handle.errors.append(
                    (f'  {RED}➜{RESET} Map file '
                     f'contains nothing but {status}', 0))
            else:
                self.handle.errors.append(
                    (f'  {RED}➜{RESET} Map file is empty', 0))
            self.handle.nb_errors += 1
            self._report(self.handle, file)
            sys.exit()

        for line, number in lines:
            try:
                if line.startswith('nb_drones'):
                    self.nb_drones = _parse_drones(line)
                elif line.startswith('hub'):
                    self.hub.append(_parse_hub(line))
                elif line.startswith('start_hub'):
                    self.start_hub = _parse_hub(line)
                elif line.startswith('end_hub'):
                    self.end_hub = _parse_hub(line)
                elif line.startswith('connection'):
                    self.connections.append(_parse_connection(line))
            except ValidationError as e:
                self.handle.nb_errors += len(e.errors())
                for err in e.errors():
                    field = '.'.join(str(p) for p in err['loc'])
                    self.handle.errors.append(
                        (f"  {RED}➜{RESET} line "
                         f"{number}: '{field}' {err['msg']}", number))
            except ValueError as e:
                self.handle.nb_errors += 1
                self.handle.errors.append((f"  {RED}➜{RESET} line {number}: {e}", 0))
        if self.start_hub is None or self.end_hub is None:
            self._report(self.handle, file)
            sys.exit() 
        self.total_hubs.append(self.start_hub)
        for hub in self.hub:
            self.total_hubs.append(hub)
        self.total_hubs.append(self.end_hub)
        if self.handle.errors:
            self._report(self.handle, file)
            sys.exit()
        return (
            Data(
            nb_drones=self.nb_drones,
            start_hub=self.start_hub,
            hub=self.hub,
            end_hub=self.end_hub,
            connection=self.connections,
            total_hubs=self.total_hubs)
        )

    @staticmethod
    def _report(handle: ErrorManagement, file: str) -> None:
        word = 'errors' if handle.nb_errors > 1 else 'error'
        handle.errors.sort(key=lambda e: e[0] if e[0] else float('inf'))

        print(f'{RED}{handle.nb_errors} {word} occurred while attempting to'
              f' parse {file}{RESET}')
        for error , _ in handle.errors:
            print(error)
        
