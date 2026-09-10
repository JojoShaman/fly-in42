from collections import OrderedDict
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


def _parse_metadata(raw: str) -> Metadata:
    meta = Metadata()
    for token in raw.split(' '):
        key, value = token.split('=')
        if key == 'zone':
            if value in _ZONES:
                meta.zone = _ZONES[value]
        elif key == 'color':
            meta.color = value
        elif key == 'max_drones':
            meta.max_drones = int(value)
    return meta


def _parse_drones(line: str) -> int:
    return int(line.split(':')[1])

def _parse_hub(line: str) -> Hub:
    body = line.split(':')[1]
    segments = [part for part in body.split('[') if part.strip()]
    name, x, y = segments[0].strip().split(' ')
    return Hub(
        name=name,
        x=int(x),
        y=int(y),
        meta_data=_parse_metadata(segments[1].rstrip(']')),
    )

def _parse_connection(line: str) -> Connection:
    tokens = line.split(': ')[1].split(' ')
    name1, name2 = tokens[0].split('-')
    if len(tokens) == 2:
        capacity = int(tokens[1].strip('[]').split('=')[1])
        meta_data = ConnectionMetadata(max_link_capacity=capacity)
    else:
        meta_data = ConnectionMetadata()
    return Connection(name1=name1, name2=name2, meta_data=meta_data)


def _read_lines(file: str) -> list[str]:
    with open(file, 'r') as f:
        content = f.read()
    return [
        line for line in content.splitlines()
        if line.strip() and not line.startswith('#')
    ]


def _keyword_errors(seen: list[str]) -> list[str]:
    first_order = list(OrderedDict.fromkeys(seen))
    last_order = list(OrderedDict.fromkeys(reversed(seen)))
    last_order.reverse()

    missing = set(KEYWORDS) - set(first_order)
    if missing:
        return [f'keyword "{name}" is missing' for name in missing]
    if first_order != KEYWORDS or last_order != KEYWORDS:
        return ['keyword in wrong position, update configuration file']
    return []


class Parsing:
    def __init__(self) -> None:
        self.nb_drones = 0
        self.start_hub: Hub | None = None
        self.hub: list[Hub] = []
        self.end_hub: Hub | None = None
        self.connections: list[Connection] = []
        self.total_hubs: list[Hub] = []

    def parse(self, file: str) -> Data:
        lines = _read_lines(file)

        errors: list[str] = []
        seen: list[str] = []
        for line in lines:
            keyword = line.split(':')[0]
            if keyword in KEYWORDS:
                seen.append(keyword)
            else:
                errors.append(f'error: {keyword} is not reconized')
        errors.extend(_keyword_errors(seen))

        if errors:
            self._report(errors)
            sys.exit()

        for line in lines:
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
            except ValidationError as exc:
                errors.extend(err['msg'] for err in exc.errors())
        if self.start_hub == None:
            raise ValueError("start_hub cannot be None")
        if self.end_hub == None:
            raise ValueError("end_hub cannot be None")
        self.total_hubs.append(self.start_hub)
        for hub in self.hub:
            self.total_hubs.append(hub)
        self.total_hubs.append(self.end_hub)
        if errors:
            self._report(errors)
            sys.exit()
        return (Data(
            nb_drones=self.nb_drones,
            start_hub=self.start_hub,
            hub=self.hub,
            end_hub=self.end_hub,
            connection=self.connections,
            total_hubs=self.total_hubs)
            )

    @staticmethod
    def _report(errors: list[str]) -> None:
        for error in errors:
            print(error)
