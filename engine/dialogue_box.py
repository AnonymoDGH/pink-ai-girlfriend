"""
Caja de dialogo con efecto de texto tipo Undertale: el texto aparece
letra por letra, y cada N letras se reproduce un "blip" corto. El
jugador puede acelerar/completar el texto con una tecla o click.
"""
from __future__ import annotations
import pygame
import textwrap
from engine.assets import load_sound

BLIP_EVERY_N_CHARS = 2          # reproducir blip cada N caracteres (no en cada uno, para no saturar)
DEFAULT_CHARS_PER_SECOND = 42


class DialogueBox:
    def __init__(self, font: pygame.font.Font, name_font: pygame.font.Font,
                 rect: pygame.Rect, chars_per_second: int = DEFAULT_CHARS_PER_SECOND,
                 text_color=(255, 255, 255), name_color=(255, 111, 165),
                 wrap_width_chars: int = 62):
        self.font = font
        self.name_font = name_font
        self.rect = rect
        self.chars_per_second = chars_per_second
        self.text_color = text_color
        self.name_color = name_color
        self.wrap_width_chars = wrap_width_chars

        self.speaker = ""
        self.full_text = ""
        self.visible_chars = 0
        self._char_accum = 0.0
        self.finished = False
        self._blip_counter = 0

        self.blip_sound = load_sound("sfx_blip.wav")

    def set_text(self, speaker: str, text: str):
        self.speaker = speaker
        self.full_text = text
        self.visible_chars = 0
        self._char_accum = 0.0
        self.finished = len(text) == 0
        self._blip_counter = 0

    def skip_to_end(self):
        self.visible_chars = len(self.full_text)
        self.finished = True

    def is_finished(self) -> bool:
        return self.finished

    def update(self, dt: float):
        if self.finished:
            return
        self._char_accum += dt * self.chars_per_second
        new_chars = int(self._char_accum)
        if new_chars > 0:
            prev = self.visible_chars
            self.visible_chars = min(len(self.full_text), self.visible_chars + new_chars)
            self._char_accum -= new_chars

            revealed = self.full_text[prev:self.visible_chars]
            for ch in revealed:
                if ch.strip():  # no sonar en espacios
                    self._blip_counter += 1
                    if self._blip_counter % BLIP_EVERY_N_CHARS == 0 and self.blip_sound:
                        self.blip_sound.play()

            if self.visible_chars >= len(self.full_text):
                self.finished = True

    def _wrapped_lines(self, text: str) -> list[str]:
        lines = []
        for paragraph in text.split("\n"):
            wrapped = textwrap.wrap(paragraph, width=self.wrap_width_chars) or [""]
            lines.extend(wrapped)
        return lines

    def draw(self, surface: pygame.Surface):
        box_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        box_surf.fill((20, 10, 15, 210))
        pygame.draw.rect(box_surf, (255, 111, 165, 255), box_surf.get_rect(), width=2)
        surface.blit(box_surf, self.rect.topleft)

        pad_x, pad_y = 24, 16

        if self.speaker:
            name_surf = self.name_font.render(self.speaker, True, self.name_color)
            surface.blit(name_surf, (self.rect.x + pad_x, self.rect.y + 8))
            text_top = self.rect.y + 8 + name_surf.get_height() + 6
        else:
            text_top = self.rect.y + pad_y

        visible_text = self.full_text[:self.visible_chars]
        lines = self._wrapped_lines(visible_text)
        y = text_top
        for line in lines:
            line_surf = self.font.render(line, True, self.text_color)
            surface.blit(line_surf, (self.rect.x + pad_x, y))
            y += line_surf.get_height() + 4

        if self.finished:
            # pequeño indicador parpadeante de "continuar"
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                indicator = self.font.render("▼", True, self.name_color)
                surface.blit(
                    indicator,
                    (self.rect.right - 34, self.rect.bottom - 30),
                )
