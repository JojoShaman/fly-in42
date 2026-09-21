from data import Hub, Data, Type
import heapq


class Graph:
    """Adjacency-matrix graph used to run Dijkstra's algorithm.

    Attributes:
        adj_matrix: Weight of the edge from row to column, 0 if absent.
        size: Number of vertices.
        vertex_data: Hub name stored at each vertex index.
    """
    def __init__(self, size: int) -> None:
        """Create an empty graph with no edges.

        Args:
            size: Number of vertices the graph will hold.
        """
        self.adj_matrix: list[list[float]] = [[0] * size for _ in range(size)]
        self.size: int = size
        self.vertex_data: list[str] = [''] * size

    def add_edge(self, u: int, v: int, weight: float) -> None:
        """Add a directed edge between two vertices.

        Args:
            u: Source vertex index.
            v: Destination vertex index.
            weight: Cost of moving from u to v.
        """
        if 0 <= u < self.size and 0 <= v < self.size:
            self.adj_matrix[u][v] = weight

    def dijkstra(self, start_vertex_data: str) -> list[int | None]:
        """Compute shortest paths from a starting hub.

        Args:
            start_vertex_data: Name of the hub to start from.

        Returns:
            For each vertex, the index of its predecessor on the
            shortest path from start, or None if unreached or if it
            is the start itself.
        """
        start_vertex: int = self.vertex_data.index(start_vertex_data)
        distances = [float('inf')] * self.size
        previous: list[int | None] = [None] * self.size
        distances[start_vertex] = 0
        pq = [(0.0, start_vertex)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > distances[u]:
                continue
            for v in range(self.size):
                if self.adj_matrix[u][v] != 0:
                    alt = d + self.adj_matrix[u][v]
                    if alt < distances[v]:
                        distances[v] = alt
                        previous[v] = u
                        heapq.heappush(pq, (alt, v))
        return previous


class Path:
    """Computes weighted shortest paths over the parsed map.

    Weights combine the fixed cost of a hub's zone type with a penalty
    proportional to how crowded that hub currently is, which spreads
    drones across parallel routes without planning them in advance.

    Args:
        data: Parsed map to route over.

    Attributes:
        lookup: Vertex index for each hub name.
        lookhub: Hub object for each hub name.
    """
    def __init__(self, data: Data) -> None:

        self._data: Data = data
        self.lookup: dict[str, int] = {
            h.name: n for n, h in enumerate(data.total_hubs)}
        self.lookhub: dict[str, Hub] = {
            h.name: h for h in data.total_hubs}
        self._names: list[str] = [h.name for h in data.total_hubs]
        self._multi: float = self.compute_multi()

    def compute_multi(self) -> float:
        """Pick the crowding-penalty multiplier for this map.

        A map whose start only feeds into a single-capacity bottleneck
        gains nothing from spreading drones across routes, so it gets a
        weak multiplier; a map with real parallel capacity gets a
        strong one to encourage using it.

        Returns:
            0.5 when the start's outgoing capacity is 1 or less,
            5.1 otherwise.
        """
        flow = 0
        for c in self._data.connection:
            if self._data.start_hub.name in (c.name1, c.name2):
                neighbour = (
                    c.name2
                    if c.name1 == self._data.start_hub.name else c.name1)
                hub = self.lookhub[neighbour]
                flow += min(
                    c.meta_data.max_link_capacity, hub.meta_data.max_drones)
        return 0.5 if flow <= 1 else 5.1

    def find_path(self, start: str,
                  links: dict[
                      tuple[str, str], int] | None = None) -> list[Hub]:
        """Find the fastest path from a hub to the goal.

        Connections whose current usage has reached their capacity are
        excluded from the graph, as are blocked zones in either
        direction. Weights favor priority zones and grow with a hub's
        occupancy so drones scatter across parallel routes.

        Args:
            start: Name of the hub to start from.
            links: Current usage per connection. When omitted, no
                connection is treated as saturated.

        Returns:
            The hubs along the path, start included. Empty list if no
            route exists.
        """
        link: dict[tuple[str, str], int] = links or {}
        g: Graph = Graph(len(self._data.total_hubs))
        g.vertex_data = self._names
        for c in self._data.connection:
            if c.name1 in self.lookup and c.name2 in self.lookup:
                key = ((c.name1, c.name2) if c.name1 < c.name2
                       else (c.name2, c.name1))
                h1, h2 = self.lookup[c.name1], self.lookup[c.name2]
                h2_data: Hub = self.lookhub[c.name2]
                h1_data: Hub = self.lookhub[c.name1]
                hub_zone: Type = h2_data.meta_data.zone
                hub_max_d: int = h2_data.meta_data.max_drones
                base: float = 2 if hub_zone == Type.restricted else 1
                occupation = h2_data.nb_drones / max(1, hub_max_d)
                multi = (self._multi
                         * (0.5 if hub_zone == Type.priority else 1.0))
                weight = base + occupation * multi
                if links is not None:
                    usage = link.get(key, 0)
                    if usage >= c.meta_data.max_link_capacity:
                        continue
                if h1_data.meta_data.zone is not Type.blocked:
                    g.add_edge(h1, h2, weight)
                if h2_data.meta_data.zone is not Type.blocked:
                    g.add_edge(h2, h1, weight)
        previous = g.dijkstra(start)
        comes_from = self.lookup[start]
        node: int | None = self.lookup[self._data.end_hub.name]
        path: list[Hub] = []
        while node is not None:
            path.append(self._data.total_hubs[node])
            node = previous[node]
        if not path or path[-1] is not self._data.total_hubs[comes_from]:
            return []
        return list(reversed(path))
