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


def find_path(data: Data, start: str,
              links: dict[tuple[str, str], int] | None = None) -> list[Hub]:
    link = links or {}
    g = Graph(len(data.total_hubs))
    for n, h in enumerate(data.total_hubs):
        g.add_vertex_data(n, h.name)
    lookup = {h.name: n for n, h in enumerate(data.total_hubs)}
    lookhub = {h.name: h for h in data.total_hubs}
    for c in data.connection:
        if c.name1 in lookup and c.name2 in lookup:
            key = ((c.name1, c.name2) if c.name1 < c.name2
                   else (c.name2, c.name1))
            h1, h2 = lookup[c.name1], lookup[c.name2]
            base = 1
            if lookhub[c.name2].meta_data.zone == Type.restricted:
                base = 2
            elif lookhub[c.name2].meta_data.zone == Type.priority:
                base = 1
            occupation = (lookhub[c.name2].nb_drones /
                          max(1, lookhub[c.name2].meta_data.max_drones))
            weight = base + occupation * 0.5
            if links is not None:
                usage = link.get(key, 0)
                if usage >= c.meta_data.max_link_capacity:
                    continue
            g.add_edge(h1, h2, weight)
    previous = g.dijkstra(start)
    comes_from = lookup[start]
    node: int | None = lookup[data.end_hub.name]
    path: list[Hub] = []
    while node is not None:
        path.append(data.total_hubs[node])
        node = previous[node]
    if not path or path[-1] is not data.total_hubs[comes_from]:
        return []
    return list(reversed(path))
