from pydantic import ValidationError
from typing import Any
from data import (
    Connection,
    ConnectionMetadata,
    Data,
    Hub,
    Metadata,
    Type,
)

KEYWORDS = [
    "nb_drones",
    "start_hub",
    "hub",
    "end_hub",
    "connection"
]

META_HUB_KEYWORDS = [
    "zone",
    "color",
    "max_drones"
]

_ZONES = {
    "normal": Type.normal,
    "restricted": Type.restricted,
    "priority": Type.priority,
    "blocked": Type.blocked,
}

RED = "\033[31m"
RESET = "\033[0m"

class ConnectionError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)

class MetadataError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)

class HubError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)

class ParsingTools:
    def __init__(self) -> None:
        self.connection_line: dict[str, list[int]] = {}
        self.hub_errors: int = 0
        self.max_drones: int = 0
        self._hubs_name: list[str] = []

    def _parse_metadata(self, raw: str | None,
                        keywords: list,
                        data_type: str) -> Metadata | ConnectionMetadata:
        meta: dict[str, Any] = {}
        max_drone_default = '1'  if data_type == 'hub' else str(self.max_drones)
        if raw is not None:
            for token in raw.split():
                if token == '=':
                    raise MetadataError(
                        "syntax error, spaces around '=' are not allowed") 
                key, sep, value = token.partition('=')
                if not sep:
                    raise MetadataError(f"'=' is missing in '{token}'")     
                if not key or not value:
                    raise MetadataError(
                        "syntax error, spaces around '=' are not allowed")
                if key not in keywords:
                    suggestion = find_similar(key, keywords)
                    if suggestion:
                        suggestion = f" Perhaps you meant '{suggestion}' ?"
                    raise MetadataError(
                        f"keyword '{key}' is not valid for "
                        f"{data_type} metadata.{suggestion}")
                if key in meta:
                    raise MetadataError(
                        f"multiple '{key}' attribute in metadata")
                if key == 'zone' and value not in _ZONES:
                    suggestion = find_similar(value, list(_ZONES))
                    if suggestion != '':
                        suggestion = f" Perhaps you meant '{suggestion}' ?"
                    raise MetadataError(
                        f"'{value}' is not a valid zone.{suggestion}")
                meta[key] = value
        if data_type == 'connection':
            return ConnectionMetadata(max_link_capacity=meta.get(
                'max_link_capacity', 1))
        if data_type in ('start_hub', 'end_hub'):
            meta.pop('max_drones', None)
        zone: Type = _ZONES[meta.get('zone', 'normal')]
        color = meta.get('color', 'none')
        max_drones = meta.get('max_drones', max_drone_default)
        return Metadata(
            zone=zone, color=color, max_drones=max_drones)  # type: ignore


    def _parse_drones(self, nb: str) -> int:
        try:
            ret = int(nb)
        except ValueError as e:
            raise ValueError(f"'nb_drones' {e}")
        if ret <= 0:
            raise ValueError("'nb_drones' should be a positive integer.")
        return ret


    def _extract_meta_block(
            self, tokens: list[str], start: int) -> str | None:
        rest = ' '.join(tokens[start:])
        if not rest:
            return None
        if rest.count('[') != 1 or rest.count(']') != 1:
            missing = '[' if rest.count('[') != 1 else ']'
            raise MetadataError(f"wrong metadata format, missing '{missing}'")
        if not rest.startswith('[') or not rest.endswith(']'):
            raise MetadataError("metadata block must be enclosed in brackets")
        return rest.strip('[]')


    def _parse_hub(self, body: str, hub_type: str) -> Hub:
        splited = body.split()
        if len(splited) < 3:
            raise HubError("hub definition requires a name, x and y")
        name, x, y = splited[0], splited[1], splited[2],
        if x.startswith('[') or y.startswith('['):
            if x.startswith('['):
                raise HubError("x and y cannot be empty")
            if y.startswith('['):
                raise HubError("y cannot be empty")
        meta = self._extract_meta_block(splited, 3) if len(splited) > 3 else None
        return Hub(
            name=name,
            x=x,  # type: ignore
            y=y,  # type: ignore
            meta_data=self._parse_metadata(
                meta, META_HUB_KEYWORDS, hub_type)  # type: ignore
        )

    def get_link(self, a: str, b: str) -> tuple[str, str]:
        a_index = self._hubs_name.index(a)
        b_index = self._hubs_name.index(b)
        return ((a, b) if a_index < b_index else (b, a))

    def _parse_connection(
            self, line: str, hubs: list[Hub], nb_line: int) -> Connection:
        self._hubs_name = [h.name for h in hubs]
        tokens = line.split()
        meta_data: ConnectionMetadata = ConnectionMetadata()
        if '-' not in tokens[0]:
            raise ConnectionError(
                "'-' is expected for connection between hubs")
        if len(tokens[0].split("-")) == 2:
            name1, name2 = tokens[0].split("-")
            if name1 != name2:
                if name1 == '' or name2 == '':
                    present = name1 if name1 != '' else name2
                    missing = 'name1' if name1 == '' else 'name2'
                    raise ConnectionError(
                        f"'{present}' is missing {missing} for connection")
                if name1 in self._hubs_name and name2 in self._hubs_name:
                    a, b = self.get_link(name1, name2)
                    if not self.connection_line.get(f'{a}-{b}'):
                        self.connection_line.setdefault(
                            f'{a}-{b}', []).append(nb_line)
                        meta = (self._extract_meta_block(tokens, 1)
                                if len(tokens) > 1 else None)
                        meta_data = self._parse_metadata(
                            meta, ['max_link_capacity'], 'connection')  # type: ignore
                    else:
                        raise ConnectionError(
                            f"connection '{a}-{b}' already exists "
                            f"at line {self.connection_line[f'{a}-{b}'][0]}")
                else:
                    if name1 not in self._hubs_name:
                        raise ConnectionError(
                            f"hub '{name1}' is not initialized")
                    elif name2 not in self._hubs_name:
                        raise ConnectionError(
                            f"hub '{name2}' is not initialized")
            else:
                raise ConnectionError(f"hub '{name1}' is connected to itself")
        else:
            raise ConnectionError(f"only 2 hubs are expected for connection, "
                                f"got {len(tokens[0].split('-'))}")      
        return Connection(name1=name1, name2=name2, meta_data=meta_data)  # type: ignore


class ErrorManagement:
    def __init__(self) -> None:
        self.errors: list[tuple[str, int]] = []
        self.nb_errors: int = 0

    def _error_manager(
            self, seen: dict[str, list[tuple[int, str]]]) -> None:
        lines: list[tuple[int, str]] = []
        for key, hubs in seen.items():
            for line, _ in hubs:
                lines.append((line, key))
        lines.sort()
        self._missing_errors(seen)
        for n, key in lines:
            if key == 'nb_drones':
                if n != 1:
                    self.nb_errors += 1
                    self.errors.append(
                        (f'  {RED}➜{RESET} line {n}: nb_drones '
                         f'should be initialized first', n))
        self._duplicate_errors(seen)

    def _duplicate_errors(
            self, seen: dict[str, list[tuple[int, str]]]) -> None:
        hubs: dict[str, list[int]] = {}
        for key in ("start_hub", "hub", "end_hub"):
            for line, data in seen.get(key, []):
                name = data.split()[0]
                hubs.setdefault(name, []).append(line)
        for h, dup in hubs.items():
            if len(dup) > 1:
                self.nb_errors += len(dup)
                lines = ", ".join(str(ln) for ln in dup)
                self.errors.append(
                    (
                        f'  {RED}➜{RESET} "{h}" appears multiple times at: '
                        f"lines {lines}",
                        0,
                    )
                )


    def _missing_errors(self, seen: dict[str, list[tuple[int, str]]]) -> None:
        for key in ("nb_drones", "start_hub", "end_hub", "connection"):
            nb: int = 0
            if key not in seen:
                self.errors.append((f'  {RED}➜{RESET} missing "{key}"', 0))
                nb += 1
            elif len(seen[key]) > 1 and not key == 'connection':
                nb += len(seen[key])
                lines = ", ".join(str(n) for n, _ in seen[key])
                error_line: int = seen[key][0][0]
                self.errors.append(
                    (
                        f'  {RED}➜{RESET} line {error_line}: "{key}" '
                        'declared more than once '
                        f"(lines {lines})",
                        error_line,
                    )
                )
            self.nb_errors += nb

def find_similar(wrong_k: str, keywords: list) -> str:
    similar: str = ""
    last_inter: set = set()
    for key in keywords:
        inter: set = set(wrong_k) & set(key)
        if len(inter) > len(last_inter):
            last_inter = inter
            similar = key
    verification = set(similar) - set(wrong_k)
    if len(verification) > len(similar) / 2:
        return ''
    return similar


class Parsing:
    def __init__(self) -> None:
        self.file: str = ''
        self.nb_drones: int = 0
        self.start_hub: Hub | None = None
        self.hub: list[Hub] = []
        self.end_hub: Hub | None = None
        self.connections: list[Connection] = []
        self.total_hubs: list[Hub] = []
        self.handle: ErrorManagement = ErrorManagement()
        self._lines: list[tuple[str, int]] = []

    def structure_validator(self) -> None:
        seen: dict[str, list[tuple[int, str]]] = {}
        if len(self._lines) > 0:
            for line, n in self._lines:
                key, body = line.split(":")
                if key.strip() in KEYWORDS:
                    seen.setdefault(
                        key.strip(), []).append((n, body.strip()))
                else:
                    self.handle.nb_errors += 1
                    suggestion = find_similar(key, KEYWORDS)
                    if suggestion != '':
                        suggestion = f" Perhaps you meant '{suggestion}' ?"
                    self.handle.errors.append(
                        (
                            f"  {RED}➜{RESET} line {n}: keyword '{key}' "
                            f"is not valid.{suggestion}", n
                        )
                    )
            self.handle._error_manager(seen)
            if self.handle.errors:
                self._report(self.handle, self.file)
                raise ValueError
        else:
            comments, empty = self._file_checker(self.file)
            if comments or empty:
                status: str = ""
                if comments and empty:
                    status = "comments and empty lines"
                else:
                    status = "comments" if comments else "empty lines"
                self.handle.errors.append(
                    (f"  {RED}➜{RESET} Map file "
                        f"contains nothing but {status}", 0)
                )
            else:
                self.handle.errors.append(
                    (f"  {RED}➜{RESET} Map file is empty", 0))
            self.handle.nb_errors += 1
            self._report(self.handle, self.file)
            raise ValueError

    def syntax_validator(self) -> None:
        tools = ParsingTools()
        for line, number in self._lines:
            key, body = line.split(':')
            try:
                if key.strip() == "nb_drones":
                    self.nb_drones = tools._parse_drones(body)
                    tools.max_drones = self.nb_drones
                elif key.strip() == "hub":
                    solo_hub = tools._parse_hub(body, key)
                    self.hub.append(solo_hub)
                    self.total_hubs.append(solo_hub)
                elif key.strip() == "start_hub":
                    self.start_hub = tools._parse_hub(body, key)
                    self.total_hubs.append(self.start_hub)
                elif key.strip() == "end_hub":
                    self.end_hub = tools._parse_hub(body, key)
                    self.total_hubs.append(self.end_hub)
                elif key.strip() == "connection":
                    if not tools.hub_errors:
                        connection = (
                            tools._parse_connection(
                                body, self.total_hubs, number))
                        self.connections.append(connection)
            except ValidationError as e:
                self.handle.nb_errors += len(e.errors())
                for err in e.errors():
                    field = ".".join(str(p) for p in err["loc"])
                    self.handle.errors.append(
                        (
                            f"  {RED}➜{RESET} line "
                            f"{number}: '{field}' {err['msg']}",
                            number,
                        )
                    )
            except (HubError, MetadataError) as e:
                tools.hub_errors += 1
                self.handle.nb_errors += 1
                self.handle.errors.append(
                    (f"  {RED}➜{RESET} line {number}: {e}", number))
            except (ConnectionError, ValueError) as e:
                self.handle.nb_errors += 1
                self.handle.errors.append(
                    (f"  {RED}➜{RESET} line {number}: {e}", number))

    def parse(self, file: str) -> Data:
        self.file = file
        self._lines = self._read_lines(file)
        try:        
            self.structure_validator()
            self.syntax_validator()
            if (self.handle.errors or (
                self.start_hub is None or self.end_hub is None)):
                self._report(self.handle, file)
                raise ValueError
        except ValueError:
            raise ValueError
        return Data(
            nb_drones=self.nb_drones,
            start_hub=self.start_hub,
            hub=self.hub,
            end_hub=self.end_hub,
            connection=self.connections,
            total_hubs=self.total_hubs,
        )

    def _read_lines(seld, file: str) -> list[tuple[str, int]]:
        with open(file, "r") as f:
            content = f.read()
        lines = [line for line in content.splitlines()
                if line.strip() and not line.startswith('#')]
        return [
            (line, n)
            for n, line in enumerate(lines, start=1)
        ]

    def _file_checker(self, file: str) -> tuple[bool, bool]:
        with open(file, "r") as f:
            content = f.read()
        comments: bool = False
        empty_lines: bool = False
        for line in content.splitlines():
            if not line.strip():
                empty_lines = True
            elif line.startswith("#"):
                comments = True
        return (comments, empty_lines)

    @staticmethod
    def _report(handle: ErrorManagement, file: str) -> None:
        word = "errors" if handle.nb_errors > 1 else "error"
        handle.errors.sort(key=lambda e: e[1] if e[1] else float("inf"))

        print(
            f"{RED}{handle.nb_errors} {word} occurred while attempting to"
            f" parse {file}{RESET}"
        )
        for error, _ in handle.errors:
            print(error)
