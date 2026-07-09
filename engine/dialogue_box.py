"""
Caja de diálogo con efecto de texto tipo Undertale: el texto aparece
letra por letra, y cada N letras se reproduce un "blip" corto. El
jugador puede acelerar/completar el texto con una tecla o click.

Versión 2.0 — GUI mejorada:
- Wrap por píxeles en lugar de por caracteres (adiós texto saliéndose).
- Escalado dinámico de fuente si el texto es muy largo.
- Paginación automática: si el texto no cabe, se divide en páginas
  y el jugador avanza haciendo click.
- Bordes redondeados, sombra suave y gradiente sutil para look más "VN moderno".
- Indicador de página (1/2, 2/3...) y de continuar, sin parpadeo molesto.
- Clipping estricto: nada se sale del cuadro, nunca.
"""

from __future__ import annotations
import pygame
from engine.assets import load_sound

BLIP_EVERY_N_CHARS = 2
DEFAULT_CHARS_PER_SECOND = 48  # un poco más rápido, se siente más fluido


def _load_font_fallback(size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("dejavusans", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


class DialogueBox:
    def __init__(self, font: pygame.font.Font, name_font: pygame.font.Font,
                 rect: pygame.Rect, chars_per_second: int = DEFAULT_CHARS_PER_SECOND,
                 text_color=(245, 245, 250), name_color=(255, 120, 170),
                 wrap_width_chars: int = 70,
                 base_font_size: int | None = None,
                 name_font_size: int | None = None):
        self.base_font = font
        self.base_name_font = name_font
        self.font = font
        self.name_font = name_font
        self.rect = rect
        self.chars_per_second = chars_per_second
        self.text_color = text_color
        self.name_color = name_color
        # wrap_width_chars se mantiene por compatibilidad, pero ya no se usa
        self.wrap_width_chars = wrap_width_chars

        self.base_font_size = base_font_size or font.get_height()
        self.name_font_size = name_font_size or name_font.get_height()

        self.speaker = ""
        self.full_text = ""

        # paginación
        self.pages: list[list[str]] = [[]]   # lista de páginas, cada página = lista de líneas
        self.current_page = 0
        self.page_char_offset = 0  # para efecto typewriter por página

        self.visible_chars = 0
        self._char_accum = 0.0
        self.finished_page = False
        self.finished_all = False
        self._blip_counter = 0

        self.blip_sound = load_sound("sfx_blip.wav")

        # estilo
        self.pad_x = 28
        self.pad_y = 18
        self.line_spacing = 4

    # ------------------------------------------------------------------
    def set_text(self, speaker: str, text: str):
        self.speaker = speaker
        self.full_text = text
        self.current_page = 0
        self.visible_chars = 0
        self._char_accum = 0.0
        self.finished_page = False
        self.finished_all = len(text) == 0
        self._blip_counter = 0

        self._rebuild_pages()

    # ------------------------------------------------------------------
    def _rebuild_pages(self):
        """Convierte el texto completo en páginas que caben visualmente."""
        # Probamos con tamaños de fuente decrecientes hasta que quepa
        # razonablemente, o hasta llegar al mínimo.
        for font_size in [
            self.base_font_size,
            int(self.base_font_size * 0.92),
            int(self.base_font_size * 0.84),
            int(self.base_font_size * 0.76),
            int(self.base_font_size * 0.68),
            16,
        ]:
            if font_size < 14:
                font_size = 14
            test_font = _load_font_fallback(font_size, bold=False)
            pages = self._paginate_text(self.full_text, test_font)
            # si cabe en 1-2 páginas, perfecto. Si necesita 3+, seguimos
            # reduciendo fuente, o aceptamos paginación.
            total_lines = sum(len(p) for p in pages)
            max_lines_per_page = self._max_lines_for_font(test_font)
            # Criterio: aceptamos si son <=3 páginas, o si ya estamos en mínimo
            if len(pages) <= 3 or font_size <= 16:
                self.font = test_font
                self.pages = pages
                break

        if not self.pages:
            self.pages = [[""]]

        # reajustar nombre si hace falta
        name_size = min(self.name_font_size, self.base_font_size + 2)
        self.name_font = _load_font_fallback(name_size, bold=True)

        self.current_page = 0
        self.visible_chars = 0
        self.finished_page = False
        self.finished_all = False

    def _max_lines_for_font(self, font: pygame.font.Font) -> int:
        name_h = self.name_font_size + 10 if self.speaker else 0
        available_h = self.rect.height - self.pad_y * 2 - name_h - 8
        line_h = font.get_linesize() + self.line_spacing
        return max(1, available_h // line_h)

    def _text_width(self) -> int:
        return self.rect.width - self.pad_x * 2 - 8

    def _wrap_paragraph_px(self, paragraph: str, font: pygame.font.Font, max_px: int) -> list[str]:
        if not paragraph:
            return [""]
        words = paragraph.split(" ")
        lines = []
        current = ""
        for w in words:
            test = (current + " " + w).strip() if current else w
            if font.size(test)[0] <= max_px:
                current = test
            else:
                if current:
                    lines.append(current)
                # palabra demasiado larga: cortar carácter a carácter
                if font.size(w)[0] > max_px:
                    chunk = ""
                    for ch in w:
                        if font.size(chunk + ch)[0] <= max_px:
                            chunk += ch
                        else:
                            if chunk:
                                lines.append(chunk)
                            chunk = ch
                    current = chunk
                else:
                    current = w
        if current or not lines:
            lines.append(current)
        return lines

    def _paginate_text(self, text: str, font: pygame.font.Font) -> list[list[str]]:
        max_w = self._text_width()
        max_lines = self._max_lines_for_font(font)
        all_lines: list[str] = []
        for paragraph in text.split("\n"):
            wrapped = self._wrap_paragraph_px(paragraph, font, max_w)
            all_lines.extend(wrapped if wrapped else [""])
        # dividir en páginas
        pages = []
        for i in range(0, len(all_lines), max_lines):
            pages.append(all_lines[i:i + max_lines])
        return pages or [[""]]

    # ------------------------------------------------------------------
    def skip_to_end(self):
        """Avanza la página actual:
        1) si el texto de la página aún se está escribiendo -> revelarlo todo
        2) si la página ya terminó -> avanzar a la siguiente
        3) si era la última -> marcar como terminado
        """
        page_text = self._current_page_full_text()
        if self.visible_chars < len(page_text):
            self.visible_chars = len(page_text)
            self.finished_page = True
            return

        # avanzar página
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.visible_chars = 0
            self._char_accum = 0.0
            self.finished_page = False
            self._blip_counter = 0
        else:
            self.finished_all = True

    def is_finished(self) -> bool:
        return self.finished_all

    def _current_page_lines(self) -> list[str]:
        if 0 <= self.current_page < len(self.pages):
            return self.pages[self.current_page]
        return []

    def _current_page_full_text(self) -> str:
        # reconstruir el texto visible de la página actual para el typewriter
        # unimos las líneas con espacio para que el conteo de caracteres sea continuo
        # pero realmente mostramos línea a línea.
        # Más simple: typewriter por caracteres del texto original mapeado a la página.
        # Aproximación práctica: usamos el texto completo recortado a lo que cabe en páginas previas.
        # Para simplificar: hacemos typewriter por líneas completas reveladas progresivamente
        # según caracteres visibles sobre el texto plano de la página.
        lines = self._current_page_lines()
        return "\n".join(lines)

    def update(self, dt: float):
        if self.finished_all or self.finished_page:
            return
        self._char_accum += dt * self.chars_per_second
        new_chars = int(self._char_accum)
        if new_chars > 0:
            page_text = self._current_page_full_text()
            prev = self.visible_chars
            self.visible_chars = min(len(page_text), self.visible_chars + new_chars)
            self._char_accum -= new_chars

            revealed = page_text[prev:self.visible_chars]
            for ch in revealed:
                if ch.strip() and ch != "\n":
                    self._blip_counter += 1
                    if self._blip_counter % BLIP_EVERY_N_CHARS == 0 and self.blip_sound:
                        try:
                            self.blip_sound.play()
                        except Exception:
                            pass
            if self.visible_chars >= len(page_text):
                self.finished_page = True

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        # Fondo con esquinas redondeadas + borde neón suave
        box_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        # sombra exterior sutil
        shadow = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 70), shadow.get_rect(), border_radius=16)
        surface.blit(shadow, (self.rect.x + 2, self.rect.y + 3))

        # gradiente vertical sutil
        for y in range(self.rect.height):
            alpha = 215 - int(25 * (y / self.rect.height))
            col = (28, 14, 22, alpha)
            pygame.draw.line(box_surf, col, (0, y), (self.rect.width, y))
        # borde
        pygame.draw.rect(box_surf, (255, 110, 170, 230), box_surf.get_rect(), width=2, border_radius=14)
        # brillo interior arriba
        pygame.draw.line(box_surf, (255, 180, 210, 40), (14, 1), (box_surf.get_width() - 14, 1), 2)

        surface.blit(box_surf, self.rect.topleft)

        # Nombre del speaker con pill background
        text_top = self.rect.y + self.pad_y
        if self.speaker:
            name_surf = self.name_font.render(self.speaker, True, (255, 255, 255))
            name_bg_w = name_surf.get_width() + 20
            name_bg_h = name_surf.get_height() + 8
            name_bg = pygame.Surface((name_bg_w, name_bg_h), pygame.SRCALPHA)
            pygame.draw.rect(name_bg, (255, 90, 150, 230), name_bg.get_rect(), border_radius=10)
            surface.blit(name_bg, (self.rect.x + self.pad_x - 4, self.rect.y + 10))
            surface.blit(name_surf, (self.rect.x + self.pad_x + 6, self.rect.y + 14))
            text_top += name_surf.get_height() + 14

        # Texto con clipping estricto
        clip_rect = pygame.Rect(
            self.rect.x + self.pad_x,
            text_top,
            self.rect.width - self.pad_x * 2,
            self.rect.bottom - text_top - self.pad_y - 10,
        )
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        lines = self._current_page_lines()
        page_text = "\n".join(lines)
        visible_text = page_text[:self.visible_chars]

        # dibujar línea por línea respetando saltos
        y = text_top
        line_height = self.font.get_linesize() + self.line_spacing
        # Para efecto typewriter real por líneas:
        # vamos consumiendo caracteres del visible_text
        remaining = visible_text
        for line in lines:
            if y + line_height > clip_rect.bottom:
                break
            # cuánto de esta línea está revelado?
            if len(remaining) >= len(line):
                draw_str = line
                remaining = remaining[len(line):]
                # quitar el \n separador si existe
                if remaining.startswith("\n"):
                    remaining = remaining[1:]
            elif len(remaining) > 0:
                draw_str = remaining
                remaining = ""
            else:
                draw_str = ""
            if draw_str:
                # sombra de texto sutil
                shadow_surf = self.font.render(draw_str, True, (10, 5, 8))
                surface.blit(shadow_surf, (self.rect.x + self.pad_x + 1, y + 1))
                line_surf = self.font.render(draw_str, True, self.text_color)
                surface.blit(line_surf, (self.rect.x + self.pad_x, y))
            y += line_height
            if not remaining and self.visible_chars < len(page_text):
                # aún no se ha revelado más, romper para no dibujar líneas vacías adelantadas
                # pero seguimos para mantener espacio? no, paramos
                pass

        surface.set_clip(old_clip)

        # Indicadores
        # contador de página si hay más de una
        if len(self.pages) > 1:
            page_str = f"{self.current_page + 1}/{len(self.pages)}"
            pg_surf = pygame.font.SysFont("dejavusans", 16).render(page_str, True, (255, 180, 210))
            surface.blit(pg_surf, (self.rect.right - pg_surf.get_width() - 18, self.rect.y + 12))

        if self.finished_page:
            # flecha continuar, pulso suave (sin parpadeo brusco)
            t = pygame.time.get_ticks() / 350.0
            import math
            bounce = int(3 * abs(math.sin(t)))
            indicator_text = "▼" if self.current_page == len(self.pages) - 1 else "▶▶"
            ind_surf = self.font.render(indicator_text, True, self.name_color)
            surface.blit(
                ind_surf,
                (self.rect.right - 36, self.rect.bottom - 28 - bounce),
            )
