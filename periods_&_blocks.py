"""A rotatable, perspective-rendered 3D periodic table.

Element facts and coordinates are bundled in elements.json. The data is based
on Periodic-Table-JSON (https://github.com/Bowserinator/Periodic-Table-JSON);
individual source URLs are retained with each record.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

import pygame


FPS = 90
DATA_FILE = Path(__file__).with_name("elements.json")

BACKGROUND = (0, 0, 0)
PANEL = (8, 9, 13)
TEXT = (225, 233, 245)
MUTED = (137, 154, 179)
ACCENT = (78, 207, 232)

BLOCK_COLORS = {
    "s": (40, 190, 196),
    "p": (157, 112, 240),
    "d": (73, 137, 226),
    "f": (230, 159, 62),
}

FACE_SHADE = {
    "front": 1.0,
    "top": 1.22,
    "right": 0.72,
    "left": 0.82,
    "back": 0.58,
    "bottom": 0.62,
}

FIELD_LABELS = {
    "atomic_mass": "Atomic mass (u)",
    "appearance": "Appearance",
    "atomic_radii": "Atomic radii (pm)",
    "block": "Block",
    "boil": "Boiling point (K)",
    "category": "Category",
    "cpk-hex": "CPK color",
    "density": "Density",
    "density_g_cm3": "Density (g/cm³)",
    "density_unit": "Density unit",
    "discovered_by": "Discovered by",
    "electron_affinity": "Electron affinity (kJ/mol)",
    "electron_configuration": "Electron configuration",
    "electron_configuration_semantic": "Shorthand configuration",
    "electronegativity_pauling": "Electronegativity (Pauling)",
    "group": "Group",
    "ionization_energies": "Ionization energies (kJ/mol)",
    "melt": "Melting point (K)",
    "molar_heat": "Molar heat (J/mol·K)",
    "named_by": "Named by",
    "number": "Atomic number",
    "period": "Period",
    "phase": "Phase at STP",
    "shells": "Electrons per shell",
    "source": "Element source",
    "symbol": "Symbol",
    "xpos": "Dataset grid column",
    "ypos": "Dataset grid row",
}


def load_elements() -> list[dict[str, Any]]:
    with DATA_FILE.open(encoding="utf-8") as data_file:
        payload = json.load(data_file)

    if not isinstance(payload, list) or len(payload) != 118:
        raise ValueError(f"{DATA_FILE.name} must contain exactly 118 element records.")

    elements = sorted(payload, key=lambda element: element["number"])
    numbers = [element["number"] for element in elements]
    if numbers != list(range(1, 119)):
        raise ValueError("Element data must contain unique atomic numbers from 1 to 118.")

    required = {"name", "symbol", "period", "group", "xpos", "ypos", "block"}
    for element in elements:
        missing = required.difference(element)
        if missing:
            raise ValueError(
                f"Element {element.get('number', '?')} is missing: "
                f"{', '.join(sorted(missing))}"
            )
    return elements


def is_f_series(element: dict[str, Any]) -> bool:
    number = element["number"]
    return 57 <= number <= 71 or 89 <= number <= 103


def table_position(element: dict[str, Any]) -> tuple[int, int]:
    """Place the f-series in periods 6 and 7 instead of detached rows."""
    if is_f_series(element):
        return element["xpos"], element["period"]
    return element["xpos"], element["ypos"]


def element_center(element: dict[str, Any]) -> tuple[float, float, float]:
    column, row = table_position(element)
    # The series recedes one element at a time: Tm/Yb/Lu and Md/No/Lr.
    series_start = 57 if element["period"] == 6 else 89
    depth = -0.7 * (element["number"] - series_start) if is_f_series(element) else 0.0
    return column - 9.5, 5.5 - row, depth


def shade(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, round(channel * amount))) for channel in color)


def element_color(element: dict[str, Any]) -> tuple[int, int, int]:
    if element["symbol"] == "H":
        return (255, 255, 255)
    if element["symbol"] == "He":
        return BLOCK_COLORS["p"]
    if element["symbol"] in {"La", "Ac"}:
        return BLOCK_COLORS["d"]
    block = "f" if is_f_series(element) else element.get("block", "s")
    return BLOCK_COLORS.get(block, (120, 145, 170))


def element_block_label(element: dict[str, Any]) -> str:
    if element["symbol"] == "H":
        return "NULL"
    if is_f_series(element):
        return "F-BLOCK"
    return f"{element.get('block', '?').upper()}-BLOCK"


def project(
    point: tuple[float, float, float],
    yaw: float,
    pitch: float,
    center: tuple[float, float],
    scale: float,
) -> tuple[tuple[float, float], float]:
    x, y, z = point
    x_rot = x * math.cos(yaw) + z * math.sin(yaw)
    z_rot = -x * math.sin(yaw) + z * math.cos(yaw)
    y_rot = y * math.cos(pitch) - z_rot * math.sin(pitch)
    z_view = y * math.sin(pitch) + z_rot * math.cos(pitch)

    camera_distance = 28.0
    perspective = camera_distance / max(8.0, camera_distance - z_view)
    return (
        center[0] + x_rot * scale * perspective,
        center[1] - y_rot * scale * perspective,
    ), z_view


def point_in_polygon(point: tuple[int, int], polygon: list[tuple[int, int]]) -> bool:
    x, y = point
    inside = False
    previous = len(polygon) - 1
    for current, (x_current, y_current) in enumerate(polygon):
        x_previous, y_previous = polygon[previous]
        crosses = (y_current > y) != (y_previous > y)
        if crosses:
            intersection = (
                (x_previous - x_current) * (y - y_current)
                / (y_previous - y_current)
                + x_current
            )
            if x < intersection:
                inside = not inside
        previous = current
    return inside


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if font.size(candidate)[0] <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        if font.size(line)[0] > max_width:
            chunk = ""
            for character in line:
                if chunk and font.size(chunk + character)[0] > max_width:
                    lines.append(chunk)
                    chunk = character
                else:
                    chunk += character
            line = chunk
        lines.append(line)
    return lines


def format_value(value: Any) -> str:
    if value is None or value == "":
        return "Not reported"
    if isinstance(value, dict):
        return "; ".join(
            f"{key.replace('_', ' ').title()}: {format_value(item)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        return ", ".join(format_value(item) for item in value) or "Not reported"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


class PeriodicTableApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("ELEMENTS / A Rotatable 3D Periodic Table")
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.elements = load_elements()
        self.selected = self.elements[0]

        self.font_title = pygame.font.SysFont("segoeui", 30, bold=True)
        self.font_heading = pygame.font.SysFont("segoeui", 23, bold=True)
        self.font_body = pygame.font.SysFont("segoeui", 17)
        self.font_small = pygame.font.SysFont("segoeui", 15)

        self.yaw = -0.2
        self.pitch = -0.45
        self.zoom = 1.0
        self.dragging = False
        self.last_mouse = (0, 0)
        self.detail_scroll = 0
        self.max_detail_scroll = 0
        self.tile_polygons: list[
            tuple[dict[str, Any], list[list[tuple[int, int]]]]
        ] = []
        self.reset_button = pygame.Rect(0, 0, 120, 30)
        self.table_rect = pygame.Rect(0, 0, 0, 0)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self._fit_cache_key: tuple[float, float, int, int, float] | None = None
        self._fit_cache: tuple[float, float, float, float, float] | None = None
        star_rng = random.Random(20261008)
        self.stars = [
            (
                star_rng.random(),
                star_rng.random(),
                star_rng.choices((1, 2), weights=(8, 2))[0],
                star_rng.randint(95, 210),
            )
            for _ in range(190)
        ]

    def layout(self) -> None:
        width, height = self.screen.get_size()
        panel_width = min(430, max(350, int(width * 0.29)))
        panel_x = width - panel_width - 20
        self.panel_rect = pygame.Rect(panel_x, 88, panel_width, height - 163)
        self.table_rect = pygame.Rect(20, 88, panel_x - 34, height - 163)
        self.reset_button = pygame.Rect(width - 146, 19, 126, 38)

    def world_scale(self) -> float:
        self._fit_table_geometry()
        assert self._fit_cache is not None
        return self._fit_cache[0]

    def table_center(self) -> tuple[float, float]:
        self._fit_table_geometry()
        assert self._fit_cache is not None
        scale, min_x, max_x, min_y, max_y = self._fit_cache
        bounds = self.table_content_rect()
        return (
            bounds.centerx - (min_x + max_x) * scale / 2,
            bounds.centery - (min_y + max_y) * scale / 2,
        )

    def table_content_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.table_rect.x + 22,
            self.table_rect.y + 40,
            max(1, self.table_rect.width - 44),
            max(1, self.table_rect.height - 88),
        )

    def cube_vertices(self, element: dict[str, Any]) -> list[tuple[float, float, float]]:
        center_x, center_y, center_z = element_center(element)
        half_x, half_y, half_z = 0.45, 0.45, 0.17
        return [
            (center_x - half_x, center_y - half_y, center_z - half_z),
            (center_x + half_x, center_y - half_y, center_z - half_z),
            (center_x + half_x, center_y + half_y, center_z - half_z),
            (center_x - half_x, center_y + half_y, center_z - half_z),
            (center_x - half_x, center_y - half_y, center_z + half_z),
            (center_x + half_x, center_y - half_y, center_z + half_z),
            (center_x + half_x, center_y + half_y, center_z + half_z),
            (center_x - half_x, center_y + half_y, center_z + half_z),
        ]

    def _fit_table_geometry(self) -> None:
        key = (self.yaw, self.pitch, self.table_rect.width, self.table_rect.height, self.zoom)
        if key == self._fit_cache_key and self._fit_cache is not None:
            return

        projected_points = [
            project(vertex, self.yaw, self.pitch, (0, 0), 1.0)[0]
            for element in self.elements
            for vertex in self.cube_vertices(element)
        ]
        min_x = min(point[0] for point in projected_points)
        max_x = max(point[0] for point in projected_points)
        min_y = min(point[1] for point in projected_points)
        max_y = max(point[1] for point in projected_points)
        bounds = self.table_content_rect()
        fit_scale = min(
            bounds.width / (max_x - min_x),
            bounds.height / (max_y - min_y),
        )
        self._fit_cache_key = key
        self._fit_cache = (
            max(1.0, fit_scale * self.zoom * 0.94),
            min_x,
            max_x,
            min_y,
            max_y,
        )

    def grid_point(
        self, column: float, row: float, depth: float = 0.0
    ) -> tuple[float, float, float]:
        return column - 9.5, 5.5 - row, depth

    def project_grid(self, column: float, row: float) -> tuple[int, int]:
        screen_point, _ = project(
            self.grid_point(column, row),
            self.yaw,
            self.pitch,
            self.table_center(),
            self.world_scale(),
        )
        return round(screen_point[0]), round(screen_point[1])

    def make_cube(
        self, element: dict[str, Any]
    ) -> tuple[list[tuple[str, tuple[tuple[int, int], ...], float]], float]:
        vertices = self.cube_vertices(element)
        face_indices = {
            "back": (0, 1, 2, 3),
            "bottom": (0, 1, 5, 4),
            "left": (0, 3, 7, 4),
            "right": (1, 2, 6, 5),
            "top": (3, 2, 6, 7),
            "front": (4, 5, 6, 7),
        }
        projected: list[tuple[str, tuple[tuple[int, int], ...], float]] = []
        depth_total = 0.0
        for face_name, indices in face_indices.items():
            face_points: list[tuple[int, int]] = []
            face_depth = 0.0
            for index in indices:
                screen_point, depth = project(
                    vertices[index],
                    self.yaw,
                    self.pitch,
                    self.table_center(),
                    self.world_scale(),
                )
                face_points.append((round(screen_point[0]), round(screen_point[1])))
                depth_total += depth
                face_depth += depth
            projected.append((face_name, tuple(face_points), face_depth / len(indices)))
        return projected, depth_total / 24

    def reset_view(self) -> None:
        self.yaw = -0.2
        self.pitch = -0.45
        self.zoom = 1.0
        self.detail_scroll = 0

    def draw_background(self) -> None:
        self.screen.fill(BACKGROUND)
        width, height = self.screen.get_size()
        for x_ratio, y_ratio, radius, brightness in self.stars:
            color = (brightness, brightness, brightness)
            pygame.draw.circle(
                self.screen,
                color,
                (round(x_ratio * width), round(y_ratio * height)),
                radius,
            )
        pygame.draw.line(self.screen, (34, 36, 42), (22, 75), (width - 22, 75), 1)

        mark_rect = pygame.Rect(22, 19, 38, 38)
        pygame.draw.rect(self.screen, (13, 26, 35), mark_rect, border_radius=11)
        pygame.draw.rect(self.screen, (30, 114, 126), mark_rect, 1, border_radius=11)
        pygame.draw.circle(self.screen, ACCENT, mark_rect.center, 4)
        pygame.draw.ellipse(self.screen, (110, 216, 225), (mark_rect.x + 8, mark_rect.y + 13, 22, 12), 1)
        pygame.draw.ellipse(self.screen, (110, 216, 225), (mark_rect.x + 13, mark_rect.y + 8, 12, 22), 1)

        title = self.font_title.render("PERIODIC TABLE", True, TEXT)
        self.screen.blit(title, (72, 16))
        subtitle = self.font_small.render("3D ELEMENT EXPLORER", True, MUTED)
        self.screen.blit(subtitle, (74, 43))

        if width >= 1080:
            status = self.font_small.render(
                "118 ELEMENTS   /   7 PERIODS",
                True,
                MUTED,
            )
            status_rect = status.get_rect(midright=(self.reset_button.left - 18, 38))
            self.screen.blit(status, status_rect)

        pygame.draw.rect(self.screen, (12, 24, 32), self.reset_button, border_radius=10)
        pygame.draw.rect(self.screen, (34, 83, 98), self.reset_button, 1, border_radius=10)
        label = self.font_small.render("RESET VIEW   R", True, (173, 225, 230))
        self.screen.blit(label, label.get_rect(center=self.reset_button.center))

        footer = pygame.Rect(20, self.screen.get_height() - 43, width - 40, 27)
        pygame.draw.rect(self.screen, (7, 9, 13), footer, border_radius=8)
        pygame.draw.rect(self.screen, (31, 34, 42), footer, 1, border_radius=8)
        control_text = (
            "DRAG TO ROTATE  ·  WHEEL TO ZOOM  ·  CLICK AN ELEMENT  ·  WHEEL OVER PANEL TO SCROLL  ·  ESC TO QUIT"
            if width >= 960
            else "DRAG TO ROTATE  ·  WHEEL TO ZOOM  ·  CLICK AN ELEMENT  ·  ESC TO QUIT"
        )
        controls = self.font_small.render(control_text, True, (160, 172, 191))
        self.screen.blit(controls, controls.get_rect(center=footer.center))

        pygame.draw.rect(
            self.screen,
            (5, 7, 11),
            self.table_rect,
            border_radius=15,
        )
        pygame.draw.rect(
            self.screen,
            (27, 34, 45),
            self.table_rect,
            1,
            border_radius=15,
        )
        section = self.font_small.render(
            "TABLE VIEW   /   GROUPS 1–18",
            True,
            (148, 163, 184),
        )
        self.screen.blit(section, (self.table_rect.x + 15, self.table_rect.y + 11))

    def draw_axis_labels(self) -> None:
        content = self.table_content_rect()
        axis_font = pygame.font.SysFont(
            "segoeui",
            max(8, min(14, round(self.world_scale() * 0.28))),
        )
        for group in range(1, 19):
            x, y = self.project_grid(group, 0.12)
            text = axis_font.render(str(group), True, MUTED)
            label_rect = text.get_rect(center=(x, y - 13))
            label_rect.clamp_ip(content)
            self.screen.blit(text, label_rect)

        for row in range(1, 8):
            x, y = self.project_grid(0.05, row)
            text = axis_font.render(str(row), True, MUTED)
            label_rect = text.get_rect(center=(x - 12, y))
            label_rect.clamp_ip(content)
            self.screen.blit(text, label_rect)

    def draw_legend(self) -> None:
        x = self.table_rect.left + 15
        y = self.table_rect.bottom - 37
        compact = self.table_rect.width < 540
        labels = (
            (("s", "S"), ("p", "P"), ("d", "D"), ("f", "F"))
            if compact
            else (("s", "S BLOCK"), ("p", "P BLOCK"), ("d", "D BLOCK"), ("f", "F BLOCK"))
        )
        for block, label in labels:
            color = BLOCK_COLORS[block]
            chip_width = 46 if compact else 76
            chip = pygame.Rect(x, y - 3, chip_width, 22)
            pygame.draw.rect(self.screen, (13, 16, 23), chip, border_radius=7)
            pygame.draw.rect(self.screen, shade(color, 0.75), chip, 1, border_radius=7)
            pygame.draw.circle(self.screen, color, (chip.x + 11, chip.centery), 3)
            text = self.font_small.render(label, True, (196, 205, 219))
            self.screen.blit(text, (chip.x + 20, chip.y + 4))
            x += chip_width + 8
        if not compact:
            note = self.font_small.render("4f / 5f SERIES · REAR DEPTH", True, MUTED)
            self.screen.blit(note, (x + 8, y + 1))

    def draw_table(self) -> None:
        self.tile_polygons.clear()
        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.table_content_rect())
        self.draw_axis_labels()
        scale = self.world_scale()
        symbol_font = pygame.font.SysFont(
            "segoeui",
            max(9, min(23, round(scale * 0.38))),
            bold=True,
        )
        number_font = pygame.font.SysFont(
            "segoeui",
            max(8, min(12, round(scale * 0.22))),
        )
        cubes = []
        for element in self.elements:
            faces, depth = self.make_cube(element)
            cubes.append((element, faces, depth))
        cubes.sort(key=lambda item: item[2])

        for element, faces, _ in cubes:
            color = element_color(element)
            polygon_faces: list[list[tuple[int, int]]] = []
            front_face: list[tuple[int, int]] = []
            for face_name, face_points, _ in sorted(
                faces, key=lambda face: face[2]
            ):
                polygon = list(face_points)
                polygon_faces.append(polygon)
                pygame.draw.polygon(
                    self.screen,
                    shade(color, FACE_SHADE[face_name]),
                    polygon,
                )
                pygame.draw.polygon(self.screen, (16, 26, 43), polygon, 1)
                if face_name == "front":
                    front_face = polygon

            if self.selected is element:
                pygame.draw.polygon(self.screen, (255, 245, 205), front_face, 2)
            if element is getattr(self, "hovered", None):
                pygame.draw.polygon(self.screen, (255, 255, 255), front_face, 2)

            center = (
                round(sum(point[0] for point in front_face) / len(front_face)),
                round(sum(point[1] for point in front_face) / len(front_face)),
            )
            symbol = symbol_font.render(element["symbol"], True, (9, 16, 29))
            self.screen.blit(symbol, symbol.get_rect(center=center))
            number = number_font.render(str(element["number"]), True, (16, 28, 44))
            self.screen.blit(number, (front_face[0][0] + 3, front_face[0][1] + 2))
            self.tile_polygons.append((element, polygon_faces))

        self.screen.set_clip(old_clip)
        self.draw_legend()

    def detail_rows(self, element: dict[str, Any], content_width: int) -> list[tuple[str, list[str]]]:
        excluded = {"name", "symbol", "number"}
        fields = [key for key in FIELD_LABELS if key in element and key not in excluded]
        fields.extend(
            key for key in element if key not in FIELD_LABELS and key not in excluded
        )
        rows: list[tuple[str, list[str]]] = []
        for key in fields:
            value = element[key]
            if key == "block" and element["symbol"] == "H":
                value = "NULL"
            if key == "density" and element.get("density_unit"):
                value = f"{format_value(value)} {element['density_unit']}"
            label = FIELD_LABELS.get(key, key.replace("_", " ").title())
            value_lines = wrap_text(format_value(value), self.font_body, content_width)
            rows.append((label, value_lines))
        return rows

    def draw_atom(self, element: dict[str, Any], area: pygame.Rect) -> None:
        shells = element["shells"]
        if not shells or sum(shells) != element["number"]:
            raise ValueError(
                f"Invalid electron shell data for {element['name']} "
                f"(atomic number {element['number']})."
            )

        color = element_color(element)
        center = (area.centerx, area.centery + 5)
        max_radius = max(
            12,
            min(
                area.width * 0.37,
                max(18, (area.height - 44) * 0.46),
            ),
        )
        phase = pygame.time.get_ticks() / 1000

        title = self.font_small.render(
            f"BOHR MODEL   /   {element['number']} ELECTRONS",
            True,
            color,
        )
        self.screen.blit(title, (area.x + 12, area.y + 9))

        for shell_index, electron_count in enumerate(shells):
            radius = max_radius * math.sqrt((shell_index + 1) / len(shells))
            ring_rect = pygame.Rect(0, 0, round(radius * 2), round(radius * 2))
            ring_rect.center = center
            pygame.draw.ellipse(self.screen, (31, 38, 50), ring_rect, 1)

            speed = 0.38 + shell_index * 0.045
            angle_offset = phase * speed * (1 if shell_index % 2 == 0 else -1)
            for electron_index in range(electron_count):
                angle = (
                    2 * math.pi * electron_index / electron_count + angle_offset
                )
                electron = (
                    round(center[0] + math.cos(angle) * radius),
                    round(center[1] + math.sin(angle) * radius),
                )
                pygame.draw.circle(self.screen, (40, 19, 29), electron, 5)
                pygame.draw.circle(self.screen, (255, 112, 137), electron, 3)

        nucleus_radius = max(10, min(21, round(max_radius * 0.42)))
        pygame.draw.circle(self.screen, (*color, 30), center, nucleus_radius + 9)
        pygame.draw.circle(self.screen, (19, 20, 26), center, nucleus_radius + 4)
        pygame.draw.circle(self.screen, color, center, nucleus_radius, 2)
        symbol = self.font_heading.render(element["symbol"], True, TEXT)
        self.screen.blit(symbol, symbol.get_rect(center=center))

        shell_text = self.font_small.render(
            "SHELLS  " + "  ·  ".join(str(count) for count in shells),
            True,
            MUTED,
        )
        shell_rect = shell_text.get_rect(
            center=(area.centerx, min(area.bottom - 11, center[1] + max_radius + 17))
        )
        self.screen.blit(shell_text, shell_rect)

    def draw_details(self) -> None:
        panel = self.panel_rect
        frame_clip = self.screen.get_clip()
        self.screen.set_clip(panel)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=14)
        pygame.draw.rect(self.screen, (39, 51, 67), panel, 1, border_radius=14)
        element = self.selected

        header = pygame.Rect(panel.x, panel.y, panel.width, 132)
        pygame.draw.rect(self.screen, (15, 16, 20), header, border_radius=14)
        pygame.draw.rect(
            self.screen,
            (15, 16, 20),
            pygame.Rect(panel.x, panel.y + 14, panel.width, header.height - 14),
        )
        block_color = element_color(element)
        eyebrow = self.font_small.render(
            f"SELECTED ELEMENT   /   {element['number']:03d}",
            True,
            block_color,
        )
        self.screen.blit(eyebrow, (panel.x + 18, panel.y + 14))
        number_badge = pygame.Rect(panel.x + 17, panel.y + 38, 43, 43)
        pygame.draw.rect(self.screen, (25, 28, 36), number_badge, border_radius=10)
        pygame.draw.rect(self.screen, shade(block_color, 0.7), number_badge, 1, border_radius=10)
        atomic_number = self.font_heading.render(
            str(element["number"]),
            True,
            block_color,
        )
        self.screen.blit(atomic_number, atomic_number.get_rect(center=number_badge.center))
        symbol = self.font_title.render(element["symbol"], True, TEXT)
        self.screen.blit(symbol, (panel.x + 72, panel.y + 36))
        name = self.font_heading.render(element["name"], True, TEXT)
        self.screen.blit(name, (panel.x + 73, panel.y + 61))

        category = self.font_small.render(
            element.get("category", "Element").upper(), True, MUTED
        )
        self.screen.blit(category, (panel.x + 19, panel.y + 88))
        block_label = element_block_label(element)
        period_group = self.font_small.render(
            f"PERIOD {element['period']}   ·   GROUP {element['group']}   ·   {block_label}",
            True,
            MUTED,
        )
        self.screen.blit(period_group, (panel.x + 19, panel.y + 108))

        content_rect = pygame.Rect(
            panel.x + 16,
            panel.y + 143,
            panel.width - 32,
            panel.height - 185,
        )
        pygame.draw.rect(self.screen, (3, 4, 7), content_rect, border_radius=9)
        desired_atom_height = min(
            250,
            max(112, round(content_rect.height * 0.52)),
        )
        atom_height = min(
            desired_atom_height,
            max(72, content_rect.height - 90),
        )
        atom_rect = pygame.Rect(
            content_rect.x + 4,
            content_rect.y + 4,
            content_rect.width - 8,
            atom_height,
        )
        self.draw_atom(element, atom_rect)

        details_rect = pygame.Rect(
            content_rect.x,
            atom_rect.bottom + 5,
            content_rect.width,
            content_rect.bottom - atom_rect.bottom - 5,
        )
        pygame.draw.line(
            self.screen,
            (35, 38, 47),
            (details_rect.x + 12, details_rect.y),
            (details_rect.right - 12, details_rect.y),
            1,
        )
        panel_clip = self.screen.get_clip()
        self.screen.set_clip(details_rect)

        rows = self.detail_rows(element, details_rect.width - 28)
        rows_start = details_rect.y + 14
        row_y = rows_start - self.detail_scroll
        for label, value_lines in rows:
            label_surface = self.font_small.render(label.upper(), True, ACCENT)
            self.screen.blit(label_surface, (details_rect.x + 12, row_y))
            row_y += 18
            for value_line in value_lines:
                value_surface = self.font_body.render(value_line, True, TEXT)
                self.screen.blit(value_surface, (details_rect.x + 12, row_y))
                row_y += self.font_body.get_linesize()
            row_y += 10

        content_end_y = row_y + self.detail_scroll
        self.max_detail_scroll = max(0, content_end_y - details_rect.bottom + 12)
        self.detail_scroll = min(self.detail_scroll, self.max_detail_scroll)
        self.screen.set_clip(panel_clip)

        config_label = self.font_small.render(
            "SCROLL FOR ALL REPORTED ELEMENT DATA", True, MUTED
        )
        self.screen.blit(config_label, (panel.x + 17, panel.bottom - 8 - 15))
        self.screen.set_clip(frame_clip)

    def update_hover(self, mouse: tuple[int, int]) -> None:
        self.hovered = None
        if not self.table_content_rect().collidepoint(mouse):
            return
        for element, polygons in reversed(self.tile_polygons):
            if any(point_in_polygon(mouse, polygon) for polygon in polygons):
                self.hovered = element
                break

    def select_at(self, mouse: tuple[int, int]) -> None:
        if not self.table_content_rect().collidepoint(mouse):
            return
        for element, polygons in reversed(self.tile_polygons):
            if any(point_in_polygon(mouse, polygon) for polygon in polygons):
                self.selected = element
                self.detail_scroll = 0
                return

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            # Escape is the only supported way to exit the fullscreen app.
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_r:
                self.reset_view()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.reset_button.collidepoint(event.pos):
                    self.reset_view()
                elif self.table_rect.collidepoint(event.pos):
                    self.select_at(event.pos)
                    self.dragging = True
                    self.last_mouse = event.pos
            elif event.button == 4:
                self.scroll_or_zoom(event.pos, 1)
            elif event.button == 5:
                self.scroll_or_zoom(event.pos, -1)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                dx = event.pos[0] - self.last_mouse[0]
                dy = event.pos[1] - self.last_mouse[1]
                self.yaw += dx * 0.008
                self.pitch = max(-1.1, min(1.1, self.pitch + dy * 0.008))
                self.last_mouse = event.pos
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_or_zoom(pygame.mouse.get_pos(), event.y)
        return True

    def scroll_or_zoom(self, mouse: tuple[int, int], direction: int) -> None:
        if self.panel_rect.collidepoint(mouse):
            self.detail_scroll = max(
                0, min(self.max_detail_scroll, self.detail_scroll - direction * 48)
            )
        else:
            self.zoom = max(0.58, min(1.65, self.zoom * (1.1**direction)))

    def run(self) -> None:
        self.layout()
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event) and running

            mouse = pygame.mouse.get_pos()
            self.update_hover(mouse)
            self.draw_background()
            self.draw_table()
            self.draw_details()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    PeriodicTableApp().run()
