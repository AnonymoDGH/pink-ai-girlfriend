"""
Sistema de animacion de personaje: respiracion/balanceo (idle sway) y
temblor nervioso (yandere/celos/miedo shake), equivalente a lo que se
hacia con ATL en Ren'Py pero en Python + pygame puro.

NOTA: el parpadeo automatico fue removido intencionalmente. La
implementacion anterior mostraba una unica imagen generica de "ojos
cerrados" (sakura_blink.png) para CUALQUIER expresion activa, lo que
causaba que la reaccion real (enojada, triste, etc.) desapareciera
por un instante y se reemplazara por una cara neutral que no
correspondia. En vez de generar una version "ojos cerrados" para cada
una de las expresiones (mucho arte adicional), se elimino el parpadeo
por completo: cada expresion ahora se muestra siempre con su imagen
correcta, sin interrupciones.
"""
from __future__ import annotations
import math
import pygame
from engine.assets import load_image

# Modos que usan temblor nervioso/erratico en vez de balanceo suave.
SHAKE_MODES = {"yandere", "jealous", "scared"}

# El estado interno usa "normal" pero el archivo de imagen se llama
# "neutral" (por convencion heredada del diseño de sprites). Este
# mapeo evita FileNotFoundError por el desajuste de nombres.
MODE_TO_IMAGE_STEM = {
    "normal": "neutral",
}

# Lista completa de expresiones soportadas por el sprite (debe reflejar
# los archivos sakura_<nombre>.png disponibles en assets/images/).
ALL_EXPRESSIONS = {
    "normal", "happy", "blush", "sad", "angry", "surprised", "sleepy",
    "playful", "jealous", "yandere", "crying", "laughing", "confused",
    "pouting", "lovestruck", "scared", "thoughtful", "smug", "determined",
    "embarrassed", "shy", "excited", "winking", "disgusted", "proud",
    "worried", "sneaky", "relieved", "starstruck", "cold",
}

# Total: 30 expresiones disponibles.


class SakuraSprite:
    """Representa a Sakura en pantalla con animacion viva. Se le indica
    el 'modo' emocional actual y ella elige automaticamente la imagen
    base y el tipo de balanceo/temblor a aplicar (sin parpadeo)."""

    def __init__(self, base_pos: tuple[int, int]):
        self.base_x, self.base_y = base_pos
        self.mode = "normal"
        self._time = 0.0

    def set_mode(self, mode: str):
        if mode not in ALL_EXPRESSIONS:
            mode = "normal"
        self.mode = mode

    def update(self, dt: float):
        self._time += dt

    def _current_offset(self) -> tuple[float, float, float]:
        """Devuelve (xoffset, yoffset, zoom) segun el tipo de movimiento
        activo para el modo actual (sway suave o temblor nervioso)."""
        if self.mode in SHAKE_MODES:
            # temblor erratico: suma de senos con distintas frecuencias/fases
            x = (
                3.2 * math.sin(self._time * 14.0)
                + 1.6 * math.sin(self._time * 27.0 + 1.3)
            )
            y = 0.0
            zoom = 1.0
        else:
            # balanceo suave tipo "respiracion"
            y = -6.0 * (0.5 - 0.5 * math.cos(self._time * (2 * math.pi / 4.4)))
            x = 0.0
            zoom = 1.0 + 0.004 * (0.5 - 0.5 * math.cos(self._time * (2 * math.pi / 4.4)))
        return x, y, zoom

    def _image_name(self) -> str:
        stem = MODE_TO_IMAGE_STEM.get(self.mode, self.mode)
        return f"sakura_{stem}.png"

    def get_surface_and_pos(self, scale_to_height: int | None = None) -> tuple[pygame.Surface, tuple[int, int]]:
        img = load_image(self._image_name())
        if scale_to_height:
            w, h = img.get_size()
            new_h = scale_to_height
            new_w = int(w * (new_h / h))
            img = pygame.transform.smoothscale(img, (new_w, new_h))

        xoff, yoff, zoom = self._current_offset()
        if zoom != 1.0:
            w, h = img.get_size()
            img = pygame.transform.smoothscale(img, (int(w * zoom), int(h * zoom)))

        rect = img.get_rect(midbottom=(self.base_x + xoff, self.base_y + yoff))
        return img, rect.topleft
