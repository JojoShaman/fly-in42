from data import Hub, Data, Type


class Graph:
    def __init__(self, size: int) -> None:
        self.adj_matrix: list[list[float]] = [[0] * size for _ in range(size)]
        self.size: int = size
        self.vertex_data: list[str] = [''] * size
        self.lookup: dict[str, int] = {}
        self.lookhub: dict[str, Hub] = {}

    def add_edge(self, u: int, v: int, weight: float) -> None:
        if 0 <= u < self.size and 0 <= v < self.size:
            self.adj_matrix[u][v] = weight

    def add_vertex_data(self, vertex: int, data: str) -> None:
        if 0 <= vertex < self.size:
            self.vertex_data[vertex] = data

    def dijkstra(self, start_vertex_data: str) -> list[int | None]:
        start_vertex = self.vertex_data.index(start_vertex_data)
        distances = [float('inf')] * self.size
        previous: list[int | None] = [None] * self.size
        distances[start_vertex] = 0
        visited = [False] * self.size

        for _ in range(self.size):
            min_distance = float('inf')
            u = None
            for i in range(self.size):
                if not visited[i] and distances[i] < min_distance:
                    min_distance = distances[i]
                    u = i
            if u is None:
                break
            visited[u] = True
            for v in range(self.size):
                if self.adj_matrix[u][v] != 0 and not visited[v]:
                    alt = distances[u] + self.adj_matrix[u][v]
                    if alt < distances[v]:
                        distances[v] = alt
                        previous[v] = u
        return (previous)


class Path:
    def __init__(self, data: Data) -> None:
        self._data: Data = data
        self.lookup: dict[str, int] = {
            h.name: n for n, h in enumerate(data.total_hubs)}
        self.lookhub: dict[str, Hub] = {
            h.name: h for h in data.total_hubs}

    def compute_multi(self) -> float:
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
        link = links or {}
        g = Graph(len(self._data.total_hubs))
        for n, h in enumerate(self._data.total_hubs):
            g.add_vertex_data(n, h.name)
        for c in self._data.connection:
            if c.name1 in self.lookup and c.name2 in self.lookup:
                key = ((c.name1, c.name2) if c.name1 < c.name2
                       else (c.name2, c.name1))
                h1, h2 = self.lookup[c.name1], self.lookup[c.name2]
                hub_zone: Type = self.lookhub[c.name2].meta_data.zone
                hub_max_d: int = self.lookhub[c.name2].meta_data.max_drones
                base: float = (2 if hub_zone == Type.restricted else 1)
                occupation = (self.lookhub[c.name2].nb_drones /
                              max(1, hub_max_d))
                multi = (self.compute_multi()
                         * (0.5 if hub_zone == Type.priority else 1.0))
                weight = base + occupation * multi
                if links is not None:
                    usage = link.get(key, 0)
                    if usage >= c.meta_data.max_link_capacity:
                        continue
                if self.lookhub[c.name1].meta_data.zone is not Type.blocked:
                    g.add_edge(h1, h2, weight)
                if self.lookhub[c.name2].meta_data.zone is not Type.blocked:
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
