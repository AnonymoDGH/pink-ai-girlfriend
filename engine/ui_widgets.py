"""
Widgets de interfaz simples reutilizables.
"""
from __future__ import annotations
import pygame
import textwrap


class StatsPanel:
    """Panel simple que muestra afecto/obsesion/dias/recuerdos."""

    def __init__(self, font: pygame.font.Font, title_font: pygame.font.Font):
        self.font = font
        self.title_font = title_font

    def draw(self, surface: pygame.Surface, game_state, rect: pygame.Rect):
        box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box.fill((20, 10, 15, 230))
        pygame.draw.rect(box, (255, 111, 165), box.get_rect(), width=2)
        surface.blit(box, rect.topleft)

        pad = 20
        y = rect.y + pad
        title = self.title_font.render("Estado de la relación", True, (255, 111, 165))
        surface.blit(title, (rect.x + pad, y))
        y += title.get_height() + 16

        self._draw_bar(surface, rect.x + pad, y, 260, 16, game_state.affection, (100, 220, 130))
        label = self.font.render(f"Afecto: {game_state.affection}/100", True, (255, 255, 255))
        surface.blit(label, (rect.x + pad + 270, y - 2))
        y += 30

        self._draw_bar(surface, rect.x + pad, y, 260, 16, game_state.obsession, (220, 90, 110))
        label = self.font.render(f"Obsesión: {game_state.obsession}/100", True, (255, 255, 255))
        surface.blit(label, (rect.x + pad + 270, y - 2))
        y += 40

        lines = [
            f"Etapa actual: {game_state.relationship_stage}",
            f"Días juntos: {game_state.days_passed}",
            f"Recuerdos guardados: {len(game_state.memories)}",
            f"Regalos dados: {len(game_state.gifts_given)}",
            "",
            "Presiona ESC, TAB o click para cerrar",
        ]
        for line in lines:
            surf = self.font.render(line, True, (230, 230, 230))
            surface.blit(surf, (rect.x + pad, y))
            y += surf.get_height() + 8

    def _draw_bar(self, surface, x, y, w, h, value, color):
        pygame.draw.rect(surface, (60, 60, 60), (x, y, w, h))
        fill_w = int(w * (max(0, min(100, value)) / 100))
        pygame.draw.rect(surface, color, (x, y, fill_w, h))
        pygame.draw.rect(surface, (200, 200, 200), (x, y, w, h), width=1)


class MemoryDiaryPanel:
    """Panel con scroll simple para revisar recuerdos guardados."""

    def __init__(self, font: pygame.font.Font, title_font: pygame.font.Font):
        self.font = font
        self.title_font = title_font
        self.scroll = 0

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 30)

    def draw(self, surface: pygame.Surface, game_state, rect: pygame.Rect):
        box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box.fill((20, 10, 15, 235))
        pygame.draw.rect(box, (255, 111, 165), box.get_rect(), width=2)
        surface.blit(box, rect.topleft)

        clip_rect = rect.inflate(-20, -70).move(0, 10)
        prev_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        pad = 20
        title = self.title_font.render(
            f"Diario de recuerdos ({len(game_state.memories)} guardados)",
            True, (255, 111, 165))
        surface.blit(title, (rect.x + pad, rect.y + pad))

        y = rect.y + pad + title.get_height() + 20 - self.scroll
        sorted_mems = sorted(game_state.memories, key=lambda m: -m.weight)[:60]
        for m in sorted_mems:
            header = self.font.render(f"Día {m.day} — {m.category} (peso {m.weight})", True, (255, 159, 197))
            surface.blit(header, (rect.x + pad, y))
            y += header.get_height() + 2
            body = self.font.render(m.text[:90], True, (255, 255, 255))
            surface.blit(body, (rect.x + pad, y))
            y += body.get_height() + 14

        surface.set_clip(prev_clip)

        footer = self.font.render("Rueda del mouse para desplazar — ESC o click para cerrar", True, (200, 200, 200))
        surface.blit(footer, (rect.x + pad, rect.bottom - 34))


class TextInputBox:
    """Caja de entrada de texto simple para escribir mensajes libres."""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect, max_length: int = 220,
                 placeholder: str = "Escribe tu propia respuesta y presiona Enter..."):
        self.font = font
        self.rect = rect
        self.max_length = max_length
        self.placeholder = placeholder
        self.text = ""
        self.active = False
        self.submitted_text: str | None = None

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.text.strip():
                    self.submitted_text = self.text.strip()
                    self.text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_ESCAPE:
                self.active = False
            else:
                if event.unicode and len(self.text) < self.max_length and event.unicode.isprintable():
                    self.text += event.unicode

    def consume_submission(self) -> str | None:
        if self.submitted_text is not None:
            val = self.submitted_text
            self.submitted_text = None
            return val
        return None

    def draw(self, surface: pygame.Surface):
        border_color = (255, 111, 165) if self.active else (120, 90, 100)
        box = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        box.fill((20, 10, 15, 235))
        pygame.draw.rect(box, border_color, box.get_rect(), width=2)
        surface.blit(box, self.rect.topleft)

        display_text = self.text
        if self.active and (pygame.time.get_ticks() // 500) % 2 == 0:
            display_text += "|"
        show_placeholder = not self.text and not self.active
        text_surf = self.font.render(
            self.placeholder if show_placeholder else display_text, True,
            (150, 150, 150) if show_placeholder else (255, 255, 255))
        surface.blit(text_surf, (self.rect.x + 14, self.rect.y + (self.rect.height - text_surf.get_height()) // 2))


class SuggestedReplyButtons:
    """Fila de botones con respuestas sugeridas por la IA, mas un boton
    final para abrir la entrada de texto libre."""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect):
        self.font = font
        self.rect = rect
        self.options: list[str] = []
        self._option_rects: list[pygame.Rect] = []
        self.free_text_rect: pygame.Rect | None = None
        self.hovered_index = -1

    def set_options(self, options: list[str]):
        self.options = list(options)
        self._layout()

    def _wrap_option(self, text: str, max_width: int) -> list[str]:
        avg_char_w = self.font.size("x")[0] or 8
        wrap_chars = max(10, (max_width - 24) // avg_char_w)
        return textwrap.wrap(text, width=wrap_chars) or [""]

    def _layout(self):
        self._option_rects = []
        y = self.rect.y
        for opt in self.options:
            lines = self._wrap_option(opt, self.rect.width)
            h = self.font.get_height() * len(lines) + 18
            r = pygame.Rect(self.rect.x, y, self.rect.width, h)
            self._option_rects.append(r)
            y += h + 8
        self.free_text_rect = pygame.Rect(self.rect.x, y, self.rect.width, self.font.get_height() + 18)

    def handle_event(self, event: pygame.event.Event):
        """Devuelve ('option', index), ('free_text', None) o None."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered_index = -1
            for i, r in enumerate(self._option_rects):
                if r.collidepoint(event.pos):
                    self.hovered_index = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self._option_rects):
                if r.collidepoint(event.pos):
                    return ("option", i)
            if self.free_text_rect and self.free_text_rect.collidepoint(event.pos):
                return ("free_text", None)
        elif event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < len(self.options):
                    return ("option", idx)
        return None

    def draw(self, surface: pygame.Surface):
        for i, (opt, r) in enumerate(zip(self.options, self._option_rects)):
            is_hover = (i == self.hovered_index)
            box = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            box.fill((60, 20, 35, 235) if is_hover else (25, 12, 18, 220))
            pygame.draw.rect(box, (255, 159, 197) if is_hover else (150, 100, 120), box.get_rect(), width=2)
            surface.blit(box, r.topleft)

            lines = self._wrap_option(opt, self.rect.width)
            ty = r.y + 9
            number_prefix = f"{i+1}. "
            for j, line in enumerate(lines):
                text = (number_prefix if j == 0 else "   ") + line
                surf = self.font.render(text, True, (255, 255, 255))
                surface.blit(surf, (r.x + 12, ty))
                ty += surf.get_height()

        if self.free_text_rect:
            r = self.free_text_rect
            box = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            box.fill((40, 20, 30, 220))
            pygame.draw.rect(box, (200, 150, 170), box.get_rect(), width=2)
            surface.blit(box, r.topleft)
            surf = self.font.render("✏️  Escribir mi propia respuesta...", True, (230, 210, 220))
            surface.blit(surf, (r.x + 12, r.y + (r.height - surf.get_height()) // 2))
