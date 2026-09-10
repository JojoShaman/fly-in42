from data import Data, Hub, Type
from pathfinding import find_path


class Drone:
    def __init__(self, path: list[Hub], n: int) -> None:
        self.x: float = path[0].x
        self.y: float = path[0].y
        self.path: list[Hub] = path
        self.turn: int = 0
        self.id = n
        self.end = False
        self.prev_hub = self.path[0]
        self.progress = 0.0
        self.target: float = 0.0
        self.flying_to: Hub = path[0]
        self.flying_link: tuple[str, str] = ('', '')
        self.step = 0

    def animate(self, dt: float, duree: float = 0.3) -> None:
        if self.progress >= 1.0:
            return
        self.progress = min(self.target, self.progress + dt / duree)
        a, b = self.prev_hub, self.flying_to or self.path[0]
        self.x = a.x + (b.x - a.x) * self.progress
        self.y = a.y + (b.y - a.y) * self.progress


class Simulation:
    def __init__(self, data: Data) -> None:
        self._data = data
        self.link_usage: dict[tuple[str, str], int] = {}
        self._path = find_path(data, 'start')
        self._drones = [
            Drone(self._path, n) for n in range(data.nb_drones)]
        self._path[0].nb_drones = data.nb_drones
        self._path[len(self._path) - 1].meta_data.max_drones = data.nb_drones
        self.in_motion: dict[Drone, Hub] = {}

    def link_key(self, a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    def to_restricted(self, drone: Drone) -> None:
        drone.step += 1
        self.link_usage[drone.flying_link] -= 1
        drone.target = 1.0
        drone.turn = 0
        drone.progress = 0.5
        new_path = find_path(self._data, drone.flying_to.name, self.link_usage)
        drone.path = new_path if new_path else [drone.flying_to]

    def blocked(self, drone: Drone) -> bool:
        return (len(drone.path) < 2
                or drone.path[1].nb_drones >=
                drone.path[1].meta_data.max_drones
                or self.link_usage.get(self.link_key(
                    drone.path[0].name, drone.path[1].name), 0) >= 1)

    def output(self) -> None:
        for d, h in self.in_motion.items():
            print(f'D{d.id}-{h.name} ', end='')
        print()

    def update_drone(self) -> None:
        for drone in sorted(self._drones, key=lambda d: len(d.path)):
            curr = drone.path[0]
            if drone.turn == 2:
                self.to_restricted(drone)
                continue
            new_path = (
                find_path(self._data, curr.name, self.link_usage)
                if self.blocked(drone) else None)
            if new_path:
                drone.path = new_path
            if len(drone.path) == 1:
                if curr.name == self._data.end_hub.name:
                    drone.end = True
                continue
            next = drone.path[1]
            if (next.nb_drones < next.meta_data.max_drones):
                key = self.link_key(curr.name, next.name)
                self.link_usage[key] = self.link_usage.get(key, 0)
                drone.flying_link = key
                curr.nb_drones -= 1
                next.nb_drones += 1
                drone.prev_hub = curr
                self.link_usage[drone.flying_link] += 1
                drone.progress = 0
                drone.flying_to = next
                if next.meta_data.zone == Type.restricted:
                    drone.target = 0.5
                    drone.turn = 2
                else:
                    drone.x = next.x
                    drone.y = next.y
                    self.link_usage[drone.flying_link] -= 1
                    new_path = find_path(
                        self._data, next.name, self.link_usage)
                    drone.path = new_path if new_path else [next]
                    drone.target = 1.0
                    drone.turn = 1
                self.in_motion[drone] = next
                drone.step += 1
        self.output()
