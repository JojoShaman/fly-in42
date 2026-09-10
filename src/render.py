import pygame
from pygame.time import Clock, get_ticks
from pygame.display import (
    get_surface,
    set_mode,
    set_icon,
    set_caption,
    update,
    Info)
from pygame import Rect, Surface, Color
from pygame.event import Event
from pygame.font import Font
from pygame.image import load
from pygame.transform import scale, smoothscale
from data import Data
from parsing import Parsing
from pathlib import Path
import colorsys
from simulation import Drone, Simulation


class Menu:
    def __init__(self, font: Font) -> None:
        self._font: Font = font
        self._files: list[Path] = sorted(Path('maps').rglob('*.txt'))
        self._index: int = 0
        self._visible: bool = False
        self._w: int = self._screen.get_width() // 4
        self._h: int = self._screen.get_height() // 16
        self._rect: Rect = Rect(self._screen.get_width() - self._w - 20,
                                self._screen.get_height() - self._h - 20,
                                self._w, self._h)
        self._tree: dict[str, list[Path]] = {}
        for p in self._files:
            self._tree.setdefault(p.parent.name, []).append(p)
        self._folder: str | None = None

    @property
    def _screen(self) -> Surface:
        return get_surface()

    def _resize(self, w: int, h: int) -> None:
        self._w, self._h = w // 4, h // 16
        self._rect = Rect(self._screen.get_width() - self._w - 20,
                          self._screen.get_height() - self._h - 20,
                          self._w, self._h)
        size: int = max(5, self._screen.get_height() // 36)
        self._font = Font('src/images/determination.ttf', size)

    def _entries(self) -> list[Path] | list[str]:
        if self._folder is None:
            return list(self._tree.keys())
        return self._tree[self._folder]

    def handle(self, event: Event) -> Path | None:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            if not self._visible:
                self._visible = True
            elif self._folder is not None:
                self._folder = None
                self._index = 0
            else:
                self._visible = False
        elif not self._visible:
            return None
        elif event.key == pygame.K_DOWN:
            self._index = (self._index + 1) % len(self._entries())
        elif event.key == pygame.K_UP:
            self._index = (self._index - 1) % len(self._entries())
        elif event.key == pygame.K_RETURN:
            if self._folder is None:
                self._folder = list(self._tree.keys())[self._index]
                self._index = 0
            else:
                folder = self._folder
                self._visible = False
                self._folder = None
                index = self._index
                self._index = 0
                return self._tree[folder][index]
        return None

    def draw(self) -> None:
        if not self._visible:
            return
        panel: Surface = Surface((self._w, self._h), pygame.SRCALPHA)
        panel.fill((15, 25, 60, 220))
        pygame.draw.rect(panel, (90, 110, 160), panel.get_rect(), 2)
        entries: list[Path] | list[str] = self._entries()
        per_p: int = (self._h - 5) // self._font.get_linesize()
        start: int = max(
            0, min(self._index - per_p // 2, len(entries) - per_p))
        start = max(0, start)
        visible: list[Path] | list[str] = entries[start:start + per_p]

        y = self._h // 4
        for i, e in enumerate(visible, start=start):
            label: Path | str = ''
            if isinstance(e, Path):
                label = e.stem
            else:
                label = str(e)
            if label == 'challenger' or label == '01_the_impossible_dream':
                tint = (get_ticks() / 700) % 1.0
                r, g, b = colorsys.hsv_to_rgb(tint, 0.95, 1.0)
                color: Color | tuple[int, int, int] = (
                    pygame.Color(int(r * 255), int(g * 255), int(b * 255)))
            else:
                color = (
                    (255, 230, 120) if i == self._index else (200, 210, 240))
            panel.blit(self._font.render(
                ("> " if i == self._index else "  ") +
                str(label), True, color), (12, y))
            y += self._font.get_linesize()
        self._screen.blit(panel, self._rect)


class Layout():
    def __init__(self, data: Data) -> None:
        self._w: int = self._screen.get_size()[0]
        self._h: int = self._screen.get_size()[1]
        self._drones: list[Drone] = []
        self._bg: Surface = load('src/images/water.png')
        self._title: Surface = load('src/images/fly-in.png')
        self._hub: Surface = load('src/images/hub4.png')
        self._hub_d: Surface = load('src/images/detail_hub.png')
        self._drone_img: Surface = load('src/images/drone.png')
        self._title_scale: Surface = scale(
            self._title, (self._w // 4.14, self._h // 13.09))
        self._background: Surface = (smoothscale(
            self._bg, (self._w, self._h)))
        self._drone_surf = scale(
            self._drone_img, (self._w/24, self._h/28))
        self._min_x: int = 0
        self._min_y: int = 0
        self._off_x: float = 0
        self._off_y: float = 0
        self._dist_x: float = 0
        self._dist_y: float = 0
        self._data: Data = data

    @property
    def _screen(self) -> Surface:
        return get_surface()

    def load_map(self, data: Data) -> None:
        self._data = data
        xs = [h.x for h in data.total_hubs]
        ys = [h.y for h in data.total_hubs]
        self._min_x, self._min_y = min(xs), min(ys)
        span_x = max(1, max(xs) - self._min_x)
        r_span_y = max(ys) - self._min_y
        span_y = max(1, r_span_y)
        high_e = self._h // 5
        low_e = self._h // 5
        side_e = self._w // 8.5
        available_x = self._w - 2 * side_e
        available_y = self._h - high_e - low_e
        self._dist_x = min(available_x / span_x, 250)
        self._dist_y = min(available_y / span_y, 250)
        self._off_x = side_e + (available_x - span_x * self._dist_x) / 2
        self._off_y = high_e + (available_y - r_span_y * self._dist_y) / 2
        self._cp_hub, self._cp_details = self.scale_hub()
        self._lines: list[tuple[tuple[int, int], tuple[int, int]]] = []
        lookup = {h.name: h for h in data.total_hubs}
        for c in data.connection:
            h1, h2 = lookup.get(c.name1), lookup.get(c.name2)
            if h1 and h2:
                self._lines.append((self.world_to_screen(h1.x, h1.y),
                                    self.world_to_screen(h2.x, h2.y)))
        self._hub_cache: dict[str, pygame.Surface] = {}

    def resize(self, w: int, h: int) -> None:
        self._w, self._h = w, h
        self._background = smoothscale(
            self._bg, (w, h))
        self._title_scale = scale(
            self._title, (w // 4.14, h // 13.09))
        self._drone_surf = scale(
            self._drone_img, (w // 24, h // 28))
        self.load_map(self._data)

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return (int((x - self._min_x) * self._dist_x + self._off_x),
                int((y - self._min_y) * self._dist_y + self._off_y))

    def scale_hub(self) -> tuple[pygame.Surface, pygame.Surface]:
        hub = self._hub
        details = self._hub_d
        size = int(min(self._dist_x, self._dist_y) * 0.6)
        size = max(20, min(80, size))
        hub = smoothscale(hub, (size, size))
        details = smoothscale(details, (size, size))
        return ((hub, details))


class Draw:
    from data import Hub

    def __init__(self, layout: Layout, simulation: Simulation) -> None:
        self._layout: Layout = layout
        self._font: Font = Font('src/images/determination.ttf', 20)
        self._map_txt: str = ""
        self._turn: int = 0
        self._sim: Simulation = simulation

    @property
    def _screen(self) -> Surface:
        return get_surface()

    def background(self) -> None:
        self._screen.blit(self._layout._background, (0, 0))

    def title(self) -> None:
        w, h = self._layout._w, self._layout._h
        rect: Rect = self._layout._title_scale.get_rect(
            center=(w // 2, h // 14))
        self._screen.blit(self._layout._title_scale, rect)

    def connections(self) -> None:
        for a, b in self._layout._lines:
            pygame.draw.line(self._screen, 'black', a, b, 5)
            pygame.draw.line(self._screen, 'white', a, b, 1)

    def tinted(self, color: str) -> Surface:
        if color == 'rainbow':
            return self._rainbow()
        if color not in self._layout._hub_cache:
            rgb = pygame.Color(color)
            rgb = pygame.Color(
                max(rgb.r, 35), max(rgb.g, 35), max(rgb.b, 35))
            img = self._layout._cp_hub.copy()
            img.fill(rgb, special_flags=pygame.BLEND_RGBA_MULT)
            img.blit(self._layout._cp_details, (0, 0))
            self._layout._hub_cache[color] = img
        return (self._layout._hub_cache[color])

    def _rainbow(self) -> Surface:
        tint = (get_ticks() / 700) % 1.0
        r, g, b = colorsys.hsv_to_rgb(tint, 0.95, 1.0)
        img = self._layout._cp_hub.copy()
        img.fill(
            pygame.Color(int(r * 255), int(g * 255), int(b * 255)),
            special_flags=pygame.BLEND_RGBA_MULT)
        img.blit(self._layout._cp_details, (0, 0))
        return img

    def _draw_hub(self, hub_data: Hub) -> None:
        color = hub_data.meta_data.color or 'grey'
        img = self.tinted(color)
        pos = self._layout.world_to_screen(hub_data.x, hub_data.y)
        self._screen.blit(img, img.get_rect(center=pos))

    def hub(self) -> None:
        for i in range(len(self._layout._data.hub)):
            self._draw_hub(self._layout._data.hub[i])
        self._draw_hub(self._layout._data.start_hub)
        self._draw_hub(self._layout._data.end_hub)

    def display_drone(self, dt: float) -> None:
        drones: list[Drone] = self._sim._drones
        for d in drones:
            d.animate(dt)
            px, py = self._layout.world_to_screen(d.x, d.y)
            rect = self._layout._drone_surf.get_rect(center=(px, py - 5))
            self._screen.blit(self._layout._drone_surf, rect)

    def resize_font(self) -> None:
        size = max(5, self._screen.get_height() // 36)
        self._font = Font('src/images/determination.ttf', size)

    def set_map_name(self, filepath: Path) -> None:
        self._map_txt = filepath.parent.name + '/ ' + filepath.stem

    def map_name(self) -> None:
        w, h = self._screen.get_width(), self._screen.get_height()
        surf = self._font.render(self._map_txt, False, 'white')
        self._screen.blit(surf, (w // 50, h - (h // 20)))

    def reset_turn(self) -> None:
        self._turn = 0

    def increase_turn(self) -> None:
        self._turn += 1

    def turn(self) -> None:
        w, h = self._screen.get_width(), self._screen.get_height()
        surf = self._font.render(f'turns: {self._turn}', False, 'white')
        self._screen.blit(surf, (w // 1.15, h / 20))


def _draw(draw: Draw, dt: float) -> None:
    draw.background()
    draw.title()
    draw.connections()
    draw.hub()
    draw.display_drone(dt)


def visualizer(data: Data, filepath: str) -> None:
    pygame.init()
    set_caption("Fly-in")
    icon = load('src/images/icon.png')
    set_icon(icon)
    screen: Surface = (set_mode(
        (1280, 720), pygame.RESIZABLE))
    font = Font('src/images/determination.ttf', 20)

    sim: Simulation = Simulation(data)
    fly_in: Layout = Layout(data)
    fly_in.load_map(data)
    fly_in.resize(*screen.get_size())
    draw: Draw = Draw(fly_in, sim)
    menu: Menu = Menu(font)

    draw.set_map_name(Path(filepath))
    running: bool = True
    clock: Clock = Clock()
    dt: float = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                w = max(400, event.w)
                h = max(300, event.h)
                if (w, h) != (event.w, event.h):
                    set_mode((w, h), pygame.RESIZABLE)
                fly_in.resize(w, h)
                menu._resize(*screen.get_size())
                draw.resize_font()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                if screen.get_flags() & pygame.FULLSCREEN:
                    screen = set_mode((1280, 720), pygame.RESIZABLE)
                else:
                    info = Info()
                    screen = set_mode(
                        (info.current_w, info.current_h), pygame.FULLSCREEN)
                fly_in.resize(*screen.get_size())
                menu._resize(*screen.get_size())
                draw.resize_font()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                sim.update_drone()
                if not all([x.end for x in sim._drones]):
                    draw.increase_turn()
            else:
                chosen = menu.handle(event)
                if chosen:
                    sim = Simulation(Parsing().parse(str(chosen)))
                    fly_in.load_map(Parsing().parse(str(chosen)))
                    draw = Draw(fly_in, sim)
                    draw.resize_font()
                    draw.set_map_name(chosen)
                    draw.reset_turn()

        _draw(draw, dt)
        menu.draw()
        draw.map_name()
        draw.turn()
        update()
        dt = clock.tick(60) / 1000
    pygame.quit()
