"""Polished launcher for the rotatable 3D periodic table.

The original Pygame application remains in periods_&_blocks.py. This subclass
adds keyboard-driven element search, subtle neon edge bloom, and a more finished
panel treatment without changing the bundled chemistry data or 3D projection.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

SOURCE_FILE = Path(__file__).with_name("periods_&_blocks.py")
SPEC = importlib.util.spec_from_file_location("periodic_table_core", SOURCE_FILE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load periodic-table core from {SOURCE_FILE}")

core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)

pygame = core.pygame


class ModernPeriodicTableApp(core.PeriodicTableApp):
    """Enhanced UI layered over the existing application."""

    def __init__(self) -> None:
        super().__init__()
        self.search_text = ""
        self.search_active = False
        self.search_rect = pygame.Rect(0, 0, 210, 30)
        self.search_clear_rect = pygame.Rect(0, 0, 0, 0)
        self.search_error_until = 0
        self.font_search = pygame.font.SysFont("segoeui", 14)
        self._ui_overlay: pygame.Surface | None = None

    def layout(self) -> None:
        super().layout()
        width = min(250, max(128, round(self.table_rect.width * 0.36)))
        self.search_rect = pygame.Rect(
            self.table_rect.right - width - 12,
            self.table_rect.y + 7,
            width,
            29,
        )
        self.search_clear_rect = pygame.Rect(
            self.search_rect.right - 25,
            self.search_rect.y,
            25,
            self.search_rect.height,
        )

    def _overlay(self) -> pygame.Surface:
        size = self.screen.get_size()
        if self._ui_overlay is None or self._ui_overlay.get_size() != size:
            self._ui_overlay = pygame.Surface(size, pygame.SRCALPHA)
        else:
            self._ui_overlay.fill((0, 0, 0, 0))
        return self._ui_overlay

    def _draw_search(self) -> None:
        rect = self.search_rect
        now = pygame.time.get_ticks()
        has_error = now < self.search_error_until
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if has_error:
            border = (255, 108, 124)
        elif self.search_active:
            border = core.ACCENT
        elif hovered:
            border = (58, 83, 105)
        else:
            border = (36, 53, 72)

        # Drop shadow and soft focus rim keep the control visually seated.
        overlay = self._overlay()
        pygame.draw.rect(overlay, (0, 0, 0, 75), rect.move(0, 3), border_radius=10)
        if self.search_active:
            pygame.draw.rect(
                overlay,
                (*core.ACCENT, 22),
                rect.inflate(6, 6),
                width=3,
                border_radius=13,
            )
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, (8, 15, 25), rect, border_radius=9)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=9)

        # Small search glyph.
        icon_center = (rect.x + 15, rect.centery)
        pygame.draw.circle(self.screen, (118, 164, 189), icon_center, 4, 1)
        pygame.draw.line(
            self.screen,
            (118, 164, 189),
            (icon_center[0] + 3, icon_center[1] + 3),
            (icon_center[0] + 6, icon_center[1] + 6),
            1,
        )

        if has_error:
            display_text, text_color = "No matching element", (255, 144, 154)
        elif self.search_text:
            display_text, text_color = self.search_text, core.TEXT
        else:
            display_text, text_color = "Search element…", (116, 135, 156)

        text_rect = pygame.Rect(rect.x + 29, rect.y + 1, rect.width - 56, rect.height - 2)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(text_rect)
        rendered = self.font_search.render(display_text, True, text_color)
        self.screen.blit(rendered, (text_rect.x, rect.y + 6))

        if self.search_active and not has_error and (now // 500) % 2 == 0:
            cursor_x = min(text_rect.right - 2, text_rect.x + rendered.get_width() + 2)
            pygame.draw.line(
                self.screen,
                core.ACCENT,
                (cursor_x, rect.y + 7),
                (cursor_x, rect.bottom - 7),
                1,
            )
        self.screen.set_clip(old_clip)

        if self.search_text:
            clear_center = (rect.right - 13, rect.centery)
            pygame.draw.line(
                self.screen,
                (126, 148, 170),
                (clear_center[0] - 3, clear_center[1] - 3),
                (clear_center[0] + 3, clear_center[1] + 3),
                1,
            )
            pygame.draw.line(
                self.screen,
                (126, 148, 170),
                (clear_center[0] + 3, clear_center[1] - 3),
                (clear_center[0] - 3, clear_center[1] + 3),
                1,
            )

    def draw_background(self) -> None:
        super().draw_background()

        # A restrained animated orbital mark adds motion to the header.
        pulse = 1.0 + 0.12 * math.sin(pygame.time.get_ticks() / 520)
        center = (41, 38)
        halo = self._overlay()
        pygame.draw.circle(halo, (*core.ACCENT, 18), center, round(13 * pulse), 2)
        pygame.draw.circle(halo, (143, 238, 247, 27), center, round(8 * pulse), 1)
        self.screen.blit(halo, (0, 0))

        self._draw_search()

    def draw_table(self) -> None:
        super().draw_table()

        # Bloom selected/hovered cube edges on a cached transparent layer.
        overlay = self._overlay()
        old_clip = overlay.get_clip()
        overlay.set_clip(self.table_content_rect())

        for element, polygons in self.tile_polygons:
            if element is not self.selected and element is not getattr(self, "hovered", None):
                continue

            color = core.element_color(element)
            is_selected = element is self.selected
            outer_alpha = 20 if is_selected else 12
            inner_alpha = 48 if is_selected else 65
            outer_width = 5 if is_selected else 4
            inner_color = core.ACCENT if is_selected else color

            for polygon in polygons:
                pygame.draw.polygon(
                    overlay,
                    (*color, outer_alpha),
                    polygon,
                    width=outer_width,
                )
                pygame.draw.polygon(
                    overlay,
                    (*inner_color, inner_alpha),
                    polygon,
                    width=2,
                )

        overlay.set_clip(old_clip)
        self.screen.blit(overlay, (0, 0))

    def draw_details(self) -> None:
        panel = self.panel_rect
        overlay = self._overlay()
        pygame.draw.rect(
            overlay,
            (0, 0, 0, 100),
            panel.move(0, 6).inflate(10, 10),
            border_radius=20,
        )
        pygame.draw.rect(
            overlay,
            (64, 176, 215, 18),
            panel.inflate(4, 4),
            width=3,
            border_radius=18,
        )
        self.screen.blit(overlay, (0, 0))

        super().draw_details()

        # Fine highlight along the panel edge, keyed to the selected element.
        edge_color = core.element_color(self.selected)
        pygame.draw.line(
            self.screen,
            edge_color,
            (panel.x + 18, panel.y + 1),
            (panel.right - 18, panel.y + 1),
            2,
        )

    def _search_and_select(self) -> None:
        query = self.search_text.strip().casefold()
        if not query:
            self.search_active = False
            return

        elements = self.elements
        match: dict[str, Any] | None = None

        # Prefer exact atomic number, symbol, or name before partial matches.
        for element in elements:
            if (
                str(element.get("number", "")) == query
                or str(element.get("symbol", "")).casefold() == query
                or str(element.get("name", "")).casefold() == query
            ):
                match = element
                break

        if match is None:
            match = next(
                (
                    element
                    for element in elements
                    if str(element.get("name", "")).casefold().startswith(query)
                    or str(element.get("symbol", "")).casefold().startswith(query)
                ),
                None,
            )

        if match is None:
            match = next(
                (
                    element
                    for element in elements
                    if query in str(element.get("name", "")).casefold()
                    or query in str(element.get("symbol", "")).casefold()
                ),
                None,
            )

        if match is None:
            self.search_error_until = pygame.time.get_ticks() + 1800
            return

        self.selected = match
        self.detail_scroll = 0
        self.search_text = ""
        self.search_active = False
        self.search_error_until = 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.search_rect.collidepoint(event.pos):
                if self.search_text and self.search_clear_rect.collidepoint(event.pos):
                    self.search_text = ""
                    self.search_error_until = 0
                self.search_active = True
                return True
            self.search_active = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SLASH and not self.search_active:
                self.search_active = True
                return True

            if self.search_active:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._search_and_select()
                    return True
                if event.key == pygame.K_BACKSPACE:
                    self.search_text = self.search_text[:-1]
                    self.search_error_until = 0
                    return True
                if event.key == pygame.K_ESCAPE:
                    self.search_active = False
                    return super().handle_event(event)
                if event.key == pygame.K_TAB:
                    self.search_active = False
                    return True
                if (
                    event.unicode
                    and event.unicode.isprintable()
                    and not (event.mod & pygame.KMOD_CTRL)
                    and len(self.search_text) < 40
                ):
                    self.search_text += event.unicode
                    self.search_error_until = 0
                return True

        return super().handle_event(event)


if __name__ == "__main__":
    ModernPeriodicTableApp().run()
