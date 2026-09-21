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
from pygame.mixer import Sound
from data import Data
from parsing import Parsing
from pathlib import Path
import colorsys
from simulation import Drone, Simulation


class Menu:
    """In-game overlay for picking a map file to load.

    Shown as a panel in the bottom-right corner. Navigates a two-level
    tree (difficulty folder, then map file) and plays background music
    tied to whichever map is currently loaded — the challenger map gets
    its own soundtrack that keeps playing across menu navigation.

    Args:
        font: Font used to render the panel's entries.

    Attributes:
        _files: All map files found under maps/, sorted.
        _music: Whether the challenger soundtrack is currently playing.
        _last_folder: Folder the last loaded map came from.
        _loaded_map: Path of the map currently loaded in the simulation.
        _index: Cursor position within the current list of entries.
        _visible: Whether the panel is shown.
        _tree: Map files grouped by their parent folder name.
        _folder: Folder currently open, or None when at the root.
    """
    def __init__(self, font: Font) -> None:
        self._font: Font = font
        self._files: list[Path] = sorted(Path('maps').rglob('*.txt'))
        self._music: bool = False
        self._last_folder: str = ''
        self._menu_sfx: Sound = pygame.mixer.Sound(
            'src/sounds/beep.mp3')
        self._menu_sfx.set_volume(0.2)
        self._select_sfx: Sound = pygame.mixer.Sound(
            'src/sounds/select.wav')
        self._select_sfx.set_volume(0.3)
        self._challenge: Sound = pygame.mixer.Sound(
            'src/sounds/soundtrack.mp3')
        self._loaded_map: Path = Path()
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
        """Recompute the panel's size, position and font for a new window.

        Args:
            w: New window width in pixels.
            h: New window height in pixels.
        """
        self._w, self._h = w // 4, h // 16
        margin = h // 36
        self._rect = Rect(w - self._w - margin, h - self._h - margin,
                          self._w, self._h)
        size: int = max(5, self._screen.get_height() // 36)
        self._font = Font('src/images/determination.ttf', size)

    def _entries(self) -> list[Path] | list[str]:
        """List what should currently be shown in the panel.

        Returns:
            Folder names when at the root, or the map files inside the
            currently open folder.
        """
        if self._folder is None:
            return list(self._tree.keys())
        return self._tree[self._folder]

    def handle(self, event: Event) -> Path | None:
        """React to one keyboard event and update the menu's state.

        Escape opens the panel, backs out of a folder, or closes it.
        Up/Down move the cursor. Enter opens a folder or picks a map.
        Music is started, stopped or faded to match navigation and
        whichever map ends up loaded.

        Args:
            event: The pygame event to process.

        Returns:
            The chosen map's path when the user picks one, otherwise
            None.
        """
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            if not self._visible:
                self._menu_sfx.play()
                self._visible = True
            elif self._folder is not None:
                self._folder = None
                self._index = 0
            else:
                self._visible = False
                if not self.challenger_playing:
                    self.play_music(False)
                else:
                    self._challenge.set_volume(0.3)
        if not self._visible:
            return None
        elif event.key == pygame.K_DOWN:
            self._index = (self._index + 1) % len(self._entries())
            self._select_sfx.play()
        elif event.key == pygame.K_UP:
            self._index = (self._index - 1) % len(self._entries())
            self._select_sfx.play()
        elif event.key == pygame.K_RETURN:
            self._menu_sfx.play()
            if self._folder is None:
                self._folder = list(self._tree.keys())[self._index]
                self._index = 0
            else:
                folder = self._folder
                self._last_folder = folder
                self._visible = False
                self._folder = None
                index = self._index
                self._index = 0
                self._loaded_map = self._tree[folder][index]
                if not self.challenger_playing:
                    self.play_music(False)
                return self._loaded_map
        if not self._folder:
            if self._index == 0:
                self._challenge.set_volume(0.3)
                if not self._music:
                    self.play_music(True)
            else:
                if self._music:
                    if not self.challenger_playing:
                        self.play_music(False)
                    self._challenge.set_volume(0.17)
        elif self._folder and not self._folder == 'challenger':
            if not self.challenger_playing:
                self.play_music(False)
        return None

    @property
    def challenger_playing(self) -> bool:
        """Whether the currently loaded map is the challenger map."""
        return (
            str(self._loaded_map) ==
            'maps/challenger/01_the_impossible_dream.txt')

    def play_music(self, toggle: bool) -> None:
        """Start or stop the challenger soundtrack.

        Args:
            toggle: True to start looping the track, False to stop it.
        """
        if toggle:
            self._challenge.play(-1)
            self._music = True
        else:
            self._challenge.stop()
            self._music = False

    def draw(self) -> None:
        """Render the panel, if visible, over the current screen."""
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
                str(label), False, color), (12, y))
            y += self._font.get_linesize()
        self._screen.blit(panel, self._rect)


class Layout():
    """Computes where hubs and drones sit on screen for a given map.

    Converts a map's world coordinates into screen pixels, keeping the
    layout centered and appropriately scaled regardless of window size.
    Owns the source images used for rendering and the caches derived
    from them (hub tinting, connection line endpoints).

    Args:
        data: Parsed map to lay out.

    Attributes:
        data: The map currently laid out.
        background: Background image scaled to the window.
        title_scale: Title image scaled to the window.
        drone_surf: Drone image scaled to the window.
        help: Help icon image.
        scale_help: Help icon scaled to its current display size.
        help_size: Rect the help icon is currently drawn at.
        cp_hub: Hub base image scaled for the current map.
        cp_details: Hub detail overlay scaled for the current map.
        hub_cache: Tinted hub images, keyed by color.
        lines: Screen-space endpoints of each connection.
    """
    def __init__(self, data: Data) -> None:
        self._w: int = self._screen.get_size()[0]
        self._h: int = self._screen.get_size()[1]
        self._drones: list[Drone] = []
        self.blip: Sound = pygame.mixer.Sound('src/sounds/beep.mp3')
        self.end_of_sim: Sound = pygame.mixer.Sound(
            'src/sounds/delivered.mp3')
        self.end_of_sim.set_volume(0.1)
        self.blip.set_volume(0.2)
        self._bg: Surface = load('src/images/background.png')
        self._title: Surface = load('src/images/fly-in.png')
        self._hub: Surface = load('src/images/hub5.png')
        self._hub_d: Surface = load('src/images/detail_hub2.png')
        self._drone_img: Surface = load('src/images/drone.png')
        self.help: Surface = load('src/images/help.png')
        self.help_size: Rect = self.help_rect()
        self._help_center: tuple[int, int] = (self._w // 38, self._w // 38)
        self.scale_help: Surface = scale(
            self.help, (self.help_size.w, self.help_size.h))
        self.title_scale: Surface = scale(
            self._title, (self._w // 4.14, self._h // 13.09))
        self.background: Surface = (scale(
            self._bg, (self._w, self._h)))
        self.drone_surf = scale(
            self._drone_img, (self._w//24, self._h//28))
        self._min_x: int = 0
        self._min_y: int = 0
        self._off_x: float = 0
        self._off_y: float = 0
        self._dist_x: float = 0
        self._dist_y: float = 0
        self.data: Data = data

    @property
    def _screen(self) -> Surface:
        return get_surface()

    def help_rect(self) -> Rect:
        """Return the help icon's resting position and size.

        Returns:
            A Rect anchored near the top-left corner, sized relative
            to the window width.
        """
        size = self._w // 38
        return Rect(size // 2, size // 2, size, size)

    def help_collide(self, increase: bool) -> None:
        """Grow or shrink the help icon around its fixed center.

        Args:
            increase: True to enlarge the icon (hovered), False to
                return it to its resting size.
        """
        size = self._w // 35 if increase else self._w // 38
        self.scale_help = scale(self.help, (size, size))
        self.help_size = self.scale_help.get_rect(
            center=self.help_rect().center)

    def load_map(self, data: Data) -> None:
        """Compute the screen layout for a new map.

        Works out the scale and offset needed to fit every hub on
        screen with even margins, then pre-scales the hub images and
        precomputes each connection's screen-space endpoints.

        Args:
            data: The parsed map to lay out.
        """
        self.data = data
        xs = [h.x for h in data.total_hubs]
        ys = [(h.y * -1) for h in data.total_hubs]
        self._min_x, self._min_y = min(xs), min(ys)
        span_x = max(1, max(xs) - self._min_x)
        r_span_y = max(ys) - self._min_y
        span_y = max(1, r_span_y)
        high_e = self._h // 5
        low_e = self._h // 5
        side_e = self._w // 8.5
        available_x = self._w - 2 * side_e
        available_y = self._h - high_e - low_e
        ceiling = min(self._w, self._h) // 3
        self._dist_x = min(available_x / span_x, ceiling)
        self._dist_y = min(available_y / span_y, ceiling)
        self._off_x = side_e + (available_x - span_x * self._dist_x) / 2
        self._off_y = high_e + (available_y - r_span_y * self._dist_y) / 2
        self.cp_hub, self.cp_details = self.scale_hub()
        self.lines: list[tuple[tuple[int, int], tuple[int, int]]] = []
        self.lines_name: list[tuple[str, str]] = []
        lookup = {h.name: h for h in data.total_hubs}
        for c in data.connection:
            h1, h2 = lookup.get(c.name1), lookup.get(c.name2)
            if h1 and h2:
                self.lines.append((self.world_to_screen(h1.x, h1.y),
                                   self.world_to_screen(h2.x, h2.y)))
                self.lines_name.append((c.name1, c.name2))

        self.hub_cache: dict[str, pygame.Surface] = {}

    def resize(self, w: int, h: int) -> None:
        """Re-scale everything for a new window size.

        Args:
            w: New window width in pixels.
            h: New window height in pixels.
        """
        self._w, self._h = w, h
        self.background = scale(
            self._bg, (w, h))
        self.title_scale = scale(
            self._title, (w // 4.14, h // 13.09))
        self.drone_surf = scale(
            self._drone_img, (w // 24, h // 28))
        self.scale_help = scale(
            self.help, (self.help_rect().w, self.help_rect().h))
        self.load_map(self.data)

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Convert map coordinates to screen pixels.

        Args:
            x: Horizontal position in map coordinates.
            y: Vertical position in map coordinates.

        Returns:
            The corresponding (x, y) pixel position on screen.
        """
        return (int((x - self._min_x) * self._dist_x + self._off_x),
                int(((y * -1) - self._min_y) * self._dist_y + self._off_y))

    def scale_hub(self) -> tuple[Surface, Surface]:
        """Scale the hub base and detail images for the current map.

        The size is derived from how closely packed hubs are, so
        crowded maps get smaller hubs and sparse ones get larger ones,
        within fixed bounds.

        Returns:
            The scaled base image and the scaled detail overlay.
        """
        hub = self._hub
        details = self._hub_d
        size = int(min(self._dist_x, self._dist_y) * 0.6)
        min_bound = self._h // 36
        max_bound = self._h // 9
        size = max(min_bound, min(max_bound, size))
        hub = smoothscale(hub, (size, size))
        details = scale(details, (size, size))
        return ((hub, details))


class Draw:
    """Renders one frame of the simulation to the screen.

    Reads positions and state from a Layout and a Simulation but owns
    no game state itself beyond what's needed for display (fonts,
    on-screen text, hover state for the help icon).

    Args:
        layout: Layout providing screen positions and images.
        simulation: Simulation providing drone and turn state.

    Attributes:
        _map_txt: Currently displayed map name.
        _turn: Current turn count shown on screen.
        _avg_turn: Current average-turns-per-drone shown on screen.
        _on_icon: Whether the cursor is currently over the help icon.
    """
    from data import Hub

    def __init__(self, layout: Layout, simulation: Simulation) -> None:
        self._layout: Layout = layout
        self._font: Font = Font('src/images/determination.ttf', 15)
        self._panel_font: Font = Font('src/images/determination.ttf', 10)
        self._info_font: Font = Font('src/images/MADEOkine.otf', 10)
        self._map_txt: str = ""
        self._turn: int = 0
        self._avg_turn: float = 0
        self._sim: Simulation = simulation
        self._on_icon: bool = False

    @property
    def _screen(self) -> Surface:
        return get_surface()

    def background(self) -> None:
        """Draw the background image."""
        self._screen.blit(self._layout.background, (0, 0))

    def title(self) -> None:
        """Draw the title image, centered near the top of the window."""
        w, h = self._screen.get_width(), self._screen.get_height()
        rect: Rect = self._layout.title_scale.get_rect(
            center=(w // 2, h // 14))
        self._screen.blit(self._layout.title_scale, rect)

    def connections(self) -> None:
        """Draw every connection as a two-tone line."""
        start = (255, 255, 255)
        end = (255, 30, 60)
        for (pos_a, pos_b), (name1, name2) in zip(
                self._layout.lines, self._layout.lines_name):
            key = (self._sim.link_key(
                (name1, self._sim.hubs[name1]),
                (name2, self._sim.hubs[name2])))
            cap = self._sim.link_cap.get(key, 1)
            usage = self._sim.link_usage.get(key, 0)
            ratio = min(1.0, usage / cap)
            r = int(start[0] + (end[0] - start[0]) * ratio)
            g = int(start[1] + (end[1] - start[1]) * ratio)
            b = int(start[2] + (end[2] - start[2]) * ratio)
            pygame.draw.line(self._screen, 'black', pos_a, pos_b, 5)
            pygame.draw.line(self._screen, (r, g, b), pos_a, pos_b, 2)

    def tinted(self, color: str) -> Surface:
        """Get a hub image tinted to the given color, from cache if possible.

        Args:
            color: Color name, or 'rainbow' for the animated effect.

        Returns:
            The tinted hub image, with its detail overlay applied.
        """
        if color == 'rainbow':
            return self._rainbow()
        if color not in self._layout.hub_cache:
            rgb = Color(color)
            rgb = Color(
                max(rgb.r, 35), max(rgb.g, 35), max(rgb.b, 35))
            img = self._layout.cp_hub.copy()
            img.fill(rgb, special_flags=pygame.BLEND_RGBA_MULT)
            img.blit(self._layout.cp_details, (0, 0))
            self._layout.hub_cache[color] = img
        return (self._layout.hub_cache[color])

    def _rainbow(self) -> Surface:
        """Build a hub image tinted with the current rainbow color.

        Returns:
            The tinted hub image for this frame.
        """
        tint = (get_ticks() / 700) % 1.0
        r, g, b = colorsys.hsv_to_rgb(tint, 0.95, 1.0)
        img = self._layout.cp_hub.copy()
        img.fill(
            pygame.Color(int(r * 255), int(g * 255), int(b * 255)),
            special_flags=pygame.BLEND_RGBA_MULT)
        img.blit(self._layout.cp_details, (0, 0))
        return img

    def _draw_hub(self, hub_data: Hub) -> None:
        """Draw a single hub at its screen position.

        Args:
            hub_data: The hub to draw.
        """
        color = hub_data.meta_data.color or 'grey'
        img = self.tinted(color)
        pos = self._layout.world_to_screen(hub_data.x, hub_data.y)
        self._screen.blit(img, img.get_rect(center=pos))

    def hub_pos(self, hub_data: Hub) -> Rect:
        """Return Rect of the hub"""
        ret = self._layout.world_to_screen(hub_data.x, hub_data.y)
        return Rect(self._layout.cp_hub.get_rect(center=ret))

    def hub(self) -> None:
        """Draw every hub on the map, including start and end."""
        for i in range(len(self._layout.data.hub)):
            self._draw_hub(self._layout.data.hub[i])
        self._draw_hub(self._layout.data.start_hub)
        self._draw_hub(self._layout.data.end_hub)

    def display_drone(self, dt: float) -> None:
        """Advance and draw every drone for this frame.

        Args:
            dt: Seconds elapsed since the previous frame.
        """
        drones: list[Drone] = self._sim.drones
        for d in drones:
            d.animate(dt)
            px, py = self._layout.world_to_screen(d.x, d.y)
            rect = self._layout.drone_surf.get_rect(center=(px, py - 5))
            self._screen.blit(self._layout.drone_surf, rect)

    def resize_font(self) -> None:
        """Recreate the fonts used for on-screen text and the help panel."""
        size = max(5, self._screen.get_height() // 46)
        p_size = max(5, self._screen.get_height() // 45)
        i_size = max(5, self._screen.get_height() // 40)
        self._font = Font('src/images/determination.ttf', size)
        self._panel_font = Font('src/images/determination.ttf', p_size)
        self._info_font = Font('src/images/MADEOkine.otf', i_size)

    def set_map_name(self, filepath: Path) -> None:
        """Set the map name shown on screen.

        Args:
            filepath: Path of the currently loaded map.
        """
        self._map_txt = filepath.parent.name + '/ ' + filepath.stem

    def map_name(self) -> None:
        """Draw the current map's name in the bottom-left corner."""
        w, h = self._screen.get_width(), self._screen.get_height()
        surf = self._font.render(self._map_txt, False, 'white')
        self._screen.blit(surf, surf.get_rect(
            bottomleft=(w // 50, h - (h // 55))))

    def reset_turn(self) -> None:
        """Reset the displayed turn counter to zero."""
        self._turn = 0

    def increase_turn(self) -> None:
        """Advance the displayed turn counter by one."""
        self._turn += 1

    def turn(self) -> None:
        """Draw the current turn count in the top-right corner."""
        w, h = self._screen.get_width(), self._screen.get_height()
        surf = self._font.render(f'turns: {self._turn}', False, 'white')
        rect = surf.get_rect(topright=(w - w // 25, h // 20))
        self._screen.blit(surf, rect)

    def avg_turn(self) -> None:
        """Compute and draw the current average turns per drone."""
        self._avg_turn = round(sum(turn.step for turn in self._sim.drones)
                               / self._layout.data.nb_drones, 1)
        w, h = self._screen.get_width(), self._screen.get_height()
        surf = self._font.render(
            f'average turns: {self._avg_turn}', False, 'white')
        rect = surf.get_rect(topright=(w - w // 33, h // 12))
        self._screen.blit(surf, rect)

    def d_per_turn(self) -> None:
        """Draw how many drones moved during the last turn."""
        w, h = self._screen.get_width(), self._screen.get_height()
        surf = self._font.render(
            f'drones moved: {self._sim.drones_moved}', False, 'white')
        rect = surf.get_rect(topright=(w - w // 25, h // 8.5))
        self._screen.blit(surf, rect)

    def help(self) -> None:
        """Draw the help icon at its current size and position."""
        self._screen.blit(self._layout.scale_help, self._layout.help_size)

    def help_panel(self) -> None:
        """Show the keyboard shortcuts panel while hovering the help icon.

        Grows the help icon and plays a sound the moment the cursor
        enters it, and shrinks it back once the cursor leaves.
        """
        if not self._layout.help_rect().collidepoint(pygame.mouse.get_pos()):
            if self._on_icon:
                self._on_icon = False
            self._layout.help_collide(False)
            return
        if not self._on_icon:
            self._on_icon = True
            self._layout.blip.play()
        self._layout.help_collide(True)
        lines: list[str] = [
            "SPACE      next turn",
            "P               auto play",
            "R               restart",
            "F               fullscreen",
            "ESC           maps menu",
        ]
        lh = self._font.get_linesize()
        margin = lh // 4
        w = max(self._panel_font.size(t)[0] for t in lines) + 2 * margin
        h = len(lines) * lh + 2 * margin
        panel = Surface((w, h), pygame.SRCALPHA)
        panel.fill((15, 25, 60, 220))
        pygame.draw.rect(panel, (90, 110, 160), panel.get_rect(), 2)
        y = margin
        for t in lines:
            panel.blit(self._panel_font.render(
                t, False, (200, 210, 240)), (margin, y))
            y += lh
        r = self._layout.help_rect()
        self._screen.blit(panel, (r.left, r.bottom + 10))

    def display_hub_info(self) -> None:
        """Draw informations about the hub, such as 'name',
         'position', 'zone type', and 'max_drones.'"""
        from data import Type
        zone_type: dict[Type, str] = {
            Type.normal: 'normal',
            Type.restricted: 'restricted',
            Type.priority: 'priority',
            Type.blocked: 'blocked'
        }
        for hub in self._layout.data.total_hubs:
            if not self.hub_pos(hub).collidepoint(pygame.mouse.get_pos()):
                continue
            line: str = (f"{hub.name}    {hub.x}, {hub.y}    "
                         f"zone={zone_type[hub.meta_data.zone]}    "
                         f"max_drones={hub.meta_data.max_drones}")
            w, h = self._screen.get_width(), self._screen.get_height()
            info_panel = self._info_font.render(line, False, 'white')
            self._screen.blit(
                info_panel, info_panel.get_rect(
                    midbottom=(w // 2, h - h // 55)))
            break


def _draw(draw: Draw, dt: float) -> None:
    """Render one full frame: background, map, drones and on-screen text.

    Args:
        draw: The Draw instance to render with.
        dt: Seconds elapsed since the previous frame.
    """
    draw.background()
    draw.help()
    draw.title()
    draw.connections()
    draw.hub()
    draw.display_drone(dt)
    draw.map_name()
    draw.turn()
    draw.avg_turn()
    draw.d_per_turn()
    draw.help_panel()
    draw.display_hub_info()


def rendering(data: Data, filepath: str) -> None:
    """Open the window and run the simulation's main loop.

    Handles fullscreen and window resizing, the map-selection menu,
    manual and automatic turn advancement, restarting the current map,
    and switching to a newly chosen one.

    Args:
        data: Initial parsed map to display.
        filepath: Path of that initial map, used for its display name
            and for restarting.
    """
    from simulation import NoPathFound
    pygame.init()
    pygame.mixer.init()
    set_caption("Fly-in")
    icon = load('src/images/icon.png')
    set_icon(icon)
    set_mode((1920, 1080), pygame.RESIZABLE)
    font = Font('src/images/determination.ttf', 15)
    current_map: Data = data
    map_path: Path = Path(filepath)
    try:
        sim: Simulation = Simulation(current_map)
    except NoPathFound as e:
        print(e)
        return
    fly_in: Layout = Layout(current_map)
    fly_in.load_map(current_map)
    draw: Draw = Draw(fly_in, sim)
    menu: Menu = Menu(font)
    last_size: tuple[int, int] = pygame.display.get_surface().get_size()
    menu._resize(*last_size)
    draw.resize_font()
    draw.set_map_name(Path(filepath))
    running: bool = True
    auto: bool = False
    next_turn_at: int = 0
    clock: Clock = Clock()
    dt: float = 0
    delivered: bool = False
    while running:
        size: tuple[int, int] = pygame.display.get_surface().get_size()
        if size != last_size:
            fly_in.resize(*size)
            menu._resize(*size)
            draw.resize_font()
            last_size = size
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                w = max(400, event.w)
                h = max(300, event.h)
                if (w, h) != (event.w, event.h):
                    set_mode((w, h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    if (pygame.display.get_surface().get_flags() &
                            pygame.FULLSCREEN):
                        set_mode((1280, 720), pygame.RESIZABLE)
                    else:
                        info = Info()
                        set_mode(
                            (info.current_w, info.current_h),
                            pygame.FULLSCREEN)
                elif event.key == pygame.K_SPACE:
                    if not all([x.end for x in sim.drones]):
                        sim.update_drone()
                        draw.increase_turn()
                elif event.key == pygame.K_p:
                    auto = not auto
                    next_turn_at = pygame.time.get_ticks()
                elif event.key == pygame.K_r:
                    try:
                        parse: Data = Parsing().parse(str(map_path))
                    except ValueError as e:
                        print(e)
                        continue
                    try:
                        new_sim = Simulation(parse)
                    except NoPathFound as e:
                        print(e)
                    else:
                        if delivered:
                            delivered = False
                        sim = new_sim
                        fly_in.load_map(current_map)
                        draw = Draw(fly_in, sim)
                        draw.set_map_name(map_path)
                        draw.reset_turn()
                        menu._resize(*size)
                        draw.resize_font()

                else:
                    chosen: Path | None = menu.handle(event)
                    if chosen:
                        try:
                            new_data: Data = Parsing().parse(str(chosen))
                        except ValueError as e:
                            print(e)
                            continue
                        try:
                            new_sim = Simulation(new_data)
                        except NoPathFound as e:
                            print(e)
                        else:
                            if auto:
                                auto = False
                            if delivered:
                                delivered = False
                            sim = new_sim
                            fly_in.load_map(new_data)
                            draw = Draw(fly_in, sim)
                            draw.set_map_name(chosen)
                            draw.reset_turn()
                            menu._resize(*size)
                            draw.resize_font()
                            current_map = new_data
                            map_path = chosen
        if auto and pygame.time.get_ticks() >= next_turn_at:
            if not all(d.end for d in sim.drones):
                sim.update_drone()
                draw.increase_turn()
                next_turn_at = pygame.time.get_ticks() + 500
        if all(d.end for d in sim.drones):
            if not delivered:
                if menu._music:
                    menu.play_music(False)
                fly_in.end_of_sim.play()
                delivered = True
            auto = False
        _draw(draw, dt)
        menu.draw()
        update()
        dt = clock.tick(60) / 1000
    pygame.quit()
