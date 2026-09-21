*This project has been created as part of the 42 curriculum by srosu.*

# Fly-in

## Description

Fly-in is a drone traffic simulator. Given a map describing a network of
zones ("hubs") and the connections between them, it routes a fleet of
drones from a start hub to a goal hub in as few simulation turns as
possible, while respecting per-zone capacity, per-connection capacity,
zone-type movement costs, and the special two-turn rule for restricted
zones.

The project is split into four independent layers:

- **Parsing** (`parsing.py`, `data.py`) — turns a map file into typed,
  validated Pydantic objects, collecting every structural and syntactic
  error found instead of stopping at the first one.
- **Pathfinding** (`pathfinding.py`) — a from-scratch Dijkstra
  implementation (no graph library) that recomputes the fastest route on
  demand, with weights that account for zone type and current occupancy.
- **Simulation** (`simulation.py`) — advances the drone fleet one turn at
  a time, enforcing every occupancy and capacity rule from the subject.
- **Rendering** (`render.py`) — a pygame interface showing the map, the
  drones in motion, a map-selection menu, and live performance metrics.

## Instructions

### Requirements

- Python 3.10 or later
- pygame, pydantic (see `pyproject.toml`)

### Installation

```bash
make install
```

### Running

```bash
make run
```

By default this loads `maps/easy/01_linear_path.txt`. To run a specific
map:

```bash
python3 src/main.py maps/hard/03_ultimate_challenge.txt
```

### Controls (graphical mode)

| Key     | Action                                |
| ------- | ------------------------------------- |
| `SPACE` | Advance the simulation by one turn    |
| `P`     | Toggle automatic turn advancement     |
| `R`     | Restart the current map               |
| `F`     | Toggle fullscreen                     |
| `ESC`   | Open the map-selection menu / go back |
| Arrows  | Navigate the menu                     |
| `ENTER` | Confirm a menu selection              |

### Debugging

```bash
make debug
```

Runs the program under `pdb`.

### Linting

```bash
make lint         # flake8 + mypy (subject-mandated flags)
make lint-strict   # flake8 + mypy --strict
```

## Algorithm choices and implementation strategy

**Pathfinding.** Routes are computed with a hand-written Dijkstra over an
adjacency-matrix graph (`pathfinding.Graph`). No shortcut library
(`networkx`, `graphlib`, ...) is used, per the subject's constraint.

Edge weights are not simple hop counts. Each edge's weight reflects the
turn cost of entering its destination zone (1 for `normal`/`priority`, 2
for `restricted`), plus a penalty proportional to how crowded that
destination currently is. This penalty is what makes the algorithm
"adaptable" across topologies (a stated requirement): on a map where the
start only feeds into a single-capacity bottleneck, spreading drones
across routes buys nothing, so the penalty is kept weak; on a map with
real parallel capacity, the penalty is made strong enough to actually
push drones onto alternate routes rather than queueing behind one
another. `Path.compute_multi()` measures the start's effective outgoing
capacity once per map and picks the multiplier accordingly.

`blocked` zones are excluded from the graph entirely (in both traversal
directions), so no path can ever be computed through one, matching the
subject's "any path using it is invalid" requirement without needing a
separate check downstream.

**Recomputing vs. caching.** Every drone recomputes its own shortest path
whenever its next step is blocked (full hub, saturated connection, or no
path at all), rather than following a path planned once at the start.
Because the weights above already encode current occupancy, this
per-drone, per-turn recomputation is what produces the traffic
distribution — no separate allocation phase is planned in advance. This
keeps the design simple (one algorithm, no scheduler) at the cost of
recomputing Dijkstra more often than a fully cached approach would;
in practice this has had no visible impact on responsiveness for the
map sizes provided.

**Turn scheduling and conflict avoidance.** Each turn, drones are
processed closest-to-goal first (`sorted(self.drones, key=lambda d:
len(d.path))`). This lets a hub freed by one drone be taken immediately
by the drone behind it within the same turn, which is what the subject
means by zones freeing capacity for the same turn they're vacated.

**Restricted zones.** A drone moving onto a restricted zone is held at
`progress = 0.5` for one full turn (reported as
`D<id>-<connection>` while in transit) before completing its move on the
following turn, and the connection it occupies is only released once it
lands. It cannot idle indefinitely mid-flight, matching the "must arrive
next turn" rule.

**Complexity.** Dijkstra uses a binary heap (`heapq`) to pick the next
vertex, so it runs in O((V + E) log V) per call rather than the O(V²)
a plain array scan would give — the neighbor scan inside the loop still
walks a full adjacency-matrix row per vertex, so the practical cost sits
between the two depending on how sparse the map is. It is called up to
once per blocked drone per turn, so worst case is O(D · (V + E) log V)
per turn for D drones — comfortably fast for the map sizes in this
project (tens of hubs, tens of drones). Memory usage is O(V²) for the
adjacency matrix, rebuilt fresh on every call rather than mutated in
place; the crowding-penalty multiplier (`compute_multi`) is computed
once per map rather than once per call, since it never depends on
current occupancy.

## Visual representation

The graphical interface (pygame) shows:

- The full map, scaled and centered to fit any window size, with hubs
  colored per their `color` metadata and connections drawn between them.
- Drones animated in real time between hubs, including a visible pause
  mid-connection when heading into a restricted zone.
- A map-selection menu (bottom-right panel) for browsing every map under
  `maps/` by difficulty folder, with contextual background music.
- Live metrics: current turn count, average turns per drone, and drones
  moved this turn — the three secondary metrics the subject lists as
  optional but encourages displaying.
- A help panel (hover the icon, top-left) listing all keyboard shortcuts.
- Fullscreen and window-resize support, so the layout never breaks
  regardless of screen size.

This goes beyond a static rendering: turns can be stepped manually,
played automatically, or restarted, so the same map can be replayed and
compared under different observation speeds without leaving the program.

## Example input and expected output

Given this minimal map (`maps/easy/00_readme_example.txt`):

```
nb_drones: 2
start_hub: start 0 0 [color=green]
hub: mid 1 0 [color=blue]
end_hub: goal 2 0 [color=red]
connection: start-mid
connection: mid-goal
```

Both `mid` and each connection default to a capacity of 1, so the two
drones cannot travel side by side and must take turns. Running:

```bash
python3 src/main.py maps/easy/00_readme_example.txt
```

and stepping through the simulation produces this turn-by-turn output:

```
D1-mid
D1-goal D2-mid
D2-goal
```

Turn 1: `D1` leaves `start` for `mid`; `D2` stays behind since `mid` is
full. Turn 2: `D1` continues on to `goal` (delivered), which frees `mid`
in the same turn `D2` moves into it. Turn 3: `D2` reaches `goal`. The
simulation ends once every drone has reached the end zone — 3 turns for
this map.

## Resources

- Dijkstra, E. W. (1959). *A note on two problems in connexion with
  graphs* — the algorithm this project's pathfinding is built on.
- [Pydantic documentation](https://docs.pydantic.dev/) — data validation
  and settings management.
- [Pygame documentation](https://www.pygame.org/docs/) — rendering,
  input handling, audio.
- [PEP 257](https://peps.python.org/pep-0257/) — docstring conventions.
- [flake8](https://flake8.pycqa.org/) / [mypy](https://mypy-lang.org/)
  documentation for the linting rules this project follows.

### AI usage

Claude (Anthropic) was used throughout this project as a debugging and
design-review partner, never as a source of code copy-pasted without
review. Concretely, it was used for:

- **Debugging.** Diagnosing specific runtime issues (state desync in the
  menu's background-music logic, a mypy/Pydantic plugin configuration
  error, resize/fullscreen inconsistencies in the pygame rendering loop)
  by walking through the actual code and tracing execution by hand
  rather than being asked to rewrite it outright.
- **Design discussion.** Talking through pathfinding trade-offs — why a
  single occupancy-based penalty needed to scale with the map's real
  parallel capacity, how to represent a drone mid-flight toward a
  restricted zone, how to structure error accumulation in the parser
  instead of stopping at the first failure, and how to reduce Dijkstra's
  per-call cost without changing its results.
- **Test-case generation.** Producing map files exercising parsing edge
  cases (malformed metadata, duplicate connections, out-of-order
  keywords, missing hubs) and stress-test maps for the routing algorithm,
  which were then run against the real parser/simulation to verify
  behavior.
- **This README.** Drafted with AI assistance and reviewed for accuracy
  against the finished implementation.