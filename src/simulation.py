from data import Data, Hub, Type
from pathfinding import Path


class Drone:
    """A drone moving across the network during the simulation.

    A drone always knows where it stands: path[0] is its current hub.
    Movement is expressed in two layers — the simulation advances it one
    hub per turn, while progress interpolates the position in between so
    the rendering looks continuous.

    Args:
        path: Hubs from the current position to the goal.
        n: Creation order, used as the drone's identifier.

    Attributes:
        x: Horizontal position in map coordinates, fractional while flying.
        y: Vertical position in map coordinates, fractional while flying.
        path: Remaining hubs, recomputed whenever the drone is blocked.
            path[0] is the current hub.
        turn: Movement state. 0 when idle, 1 after a normal move, 2 while
            waiting out the extra turn a restricted hub costs.
        id: Creation order of the drone.
        prev_hub: Hub the drone took off from, used as the interpolation start.
        progress: Position along the current segment, between 0 and 1.
        target: Value progress stops at. 0.5 holds the drone mid-air for a
            turn on the way to a restricted hub, 1.0 lets it land.
        flying_to: Hub the drone is heading for.
        flying_link: Connection currently occupied, kept so the usage
            counter can be released on landing.
        step: Number of moves made so far.
    """
    def __init__(self, path: list[Hub], n: int) -> None:
        self.x: float = path[0].x
        self.y: float = path[0].y
        self.path: list[Hub] = path
        self.turn: int = 0
        self.id: int = n
        self.end: bool = False
        self.prev_hub: Hub = self.path[0]
        self.progress: float = 0.0
        self.target: float = 0.0
        self.flying_to: Hub = path[0]
        self.flying_link: tuple[str, str] = ('', '')
        self.step: int = 0

    def animate(self, dt: float, duree: float = 0.4) -> None:
        """Advance the visual interpolation between two hubs.

        Called once per frame, independently of the turn-based logic.
        The drone slides from prev_hub towards flying_to until progress
        reaches target.

        Args:
            dt: Seconds elapsed since the previous frame.
            duration: Seconds a full segment takes to cross.
        """
        if self.progress >= 1.0:
            return
        self.progress = min(self.target, self.progress + dt / duree)
        a, b = self.prev_hub, self.flying_to or self.path[0]
        self.x = a.x + (b.x - a.x) * self.progress
        self.y = a.y + (b.y - a.y) * self.progress


class NoPathFound(Exception):
    """Raised when the map offers no route from start to goal.

    Args:
        msg: Message shown to the user.
    """
    def __init__(self, msg: str = "No path was found") -> None:
        super().__init__('Error: ' + msg)


class Simulation:
    """Runs the drone traffic, one turn at a time.

    Each drone recomputes its own route when its way is blocked, and the
    weights used for that account for how crowded the hubs are. Drones
    therefore spread over parallel routes on their own, without any
    global allocation being planned up front.

    Args:
        data: Parsed map. Hub occupancy counters are updated in place as
            the simulation runs.

    Attributes:
        link_usage: Drones currently flying over each connection.
        link_cap: How many drones each connection takes at once.
        drones: Every drone, whether waiting, flying or arrived.
        in_motion: Hub each drone is heading for this turn.
        drones_moved: Drones that made progress during the last turn.

    Raises:
        NoPathFound: If no route exists between start and goal.
    """
    def __init__(self, data: Data) -> None:
        self._data = data
        self.link_usage: dict[tuple[str, str], int] = {}
        self.hubs: dict[str, int] = {h.name : pos for pos, h in enumerate(data.total_hubs)}
        self.link_cap: dict[tuple[str, str], int] = {
            self.link_key((c.name1, self.hubs[c.name1]), (c.name2, self.hubs[c.name2])): c.meta_data.max_link_capacity
            for c in data.connection}
        self._path_obj: Path = Path(data)
        self._path: list[Hub] = self._path_obj.find_path(data.start_hub.name)
        if not self._path:
            raise NoPathFound
        self.drones = [
            Drone(self._path, n) for n in range(data.nb_drones)]
        self._path[0].nb_drones = data.nb_drones
        self._path[len(self._path) - 1].meta_data.max_drones = data.nb_drones
        self.in_motion: dict[Drone, str] = {}
        self.drones_moved: int = 0

    def link_key(self, a: tuple[str, int], b: tuple[str, int]) -> tuple[str, str]:
        """Build the lookup key identifying a connection.

        Connections are bidirectional, so the two names are sorted to give
        A-to-B and B-to-A the same key.

        Args:
            a: Name of one end of the connection.
            b: Name of the other end.

        Returns:
            The two names in alphabetical order.
        """
        return (a[0], b[0]) if a[1] < b[1] else (b[0], a[0])

    def to_restricted(self, drone: Drone) -> None:
        """Land a drone that spent its extra turn over a restricted hub.

        Releases the connection, completes the interpolation and picks up
        the route from the hub just reached.

        Args:
            drone: A drone whose turn state is 2.
        """
        self.in_motion[drone] = drone.flying_to.name
        drone.step += 1
        self.link_usage[drone.flying_link] -= 1
        drone.target = 1.0
        drone.turn = 0
        drone.progress = 0.5
        new_path = self._path_obj.find_path(
            drone.flying_to.name, self.link_usage)
        drone.path = new_path if new_path else [drone.flying_to]
        self.drones_moved += 1

    def blocked(self, drone: Drone) -> bool:
        """Tell whether the drone can take its next step.

        Args:
            drone: The drone to test.

        Returns:
            True when the drone has nowhere left to go, the next hub is
            full, or the connection to it is saturated.
        """
        if len(drone.path) < 2:
            return True
        next_h = drone.path[1]
        if next_h.nb_drones >= next_h.meta_data.max_drones:
            return True
        curr_h = drone.path[0]
        key = self.link_key(
            (curr_h.name, self.hubs[curr_h.name]),
            (next_h.name, self.hubs[next_h.name]))
        return self.link_usage.get(key, 0) >= self.link_cap.get(key, 1)

    def output(self) -> None:
        """Print the hub each moving drone is heading for this turn."""
        for d, positon in self.in_motion.items():
            print(f'D{d.id}-{positon} ', end='')
        print()

    def update_drone(self) -> None:
        """Play one turn, moving every drone that can advance.

        Drones are handled closest-to-goal first, so a hub freed by one
        drone can be taken by the one behind it within the same turn.
        """
        self.drones_moved = 0
        for drone in sorted(self.drones, key=lambda d: len(d.path)):
            curr = drone.path[0]
            if drone.turn == 2:
                self.to_restricted(drone)
                continue
            is_blocked = self.blocked(drone)
            if is_blocked:
                new_path = (
                    self._path_obj.find_path(curr.name, self.link_usage))
                if new_path:
                    drone.path = new_path
                    is_blocked = self.blocked(drone)
            if len(drone.path) == 1:
                continue
            next_h = drone.path[1]
            if not is_blocked:
                key = self.link_key(
                    (curr.name, self.hubs[curr.name]),
                    (next_h.name, self.hubs[next_h.name]))
                self.link_usage[key] = self.link_usage.get(key, 0)
                drone.flying_link = key
                curr.nb_drones -= 1
                next_h.nb_drones += 1
                drone.prev_hub = curr
                self.link_usage[drone.flying_link] += 1
                drone.progress = 0
                drone.flying_to = next_h
                if next_h.meta_data.zone == Type.restricted:
                    position = '-'.join(drone.flying_link)
                    drone.target = 0.5
                    drone.turn = 2
                else:
                    drone.x = next_h.x
                    drone.y = next_h.y
                    self.link_usage[drone.flying_link] -= 1
                    new_path = self._path_obj.find_path(
                        next_h.name, self.link_usage)
                    drone.path = new_path if new_path else [next_h]
                    if drone.path[0].name == self._data.end_hub.name:
                        drone.end = True
                    drone.target = 1.0
                    drone.turn = 1
                    position = next_h.name
                self.in_motion[drone] = position
                drone.step += 1
                self.drones_moved += 1
        self.output()
