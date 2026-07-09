"""
Carga y cache centralizado de imagenes y sonidos, para no repetir
pygame.image.load()/mixer.Sound() por todo el codigo del juego.
"""
from __future__ import annotations
import os
import pygame

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")

_image_cache: dict[str, pygame.Surface] = {}
_sound_cache: dict[str, pygame.mixer.Sound] = {}


def load_image(name: str) -> pygame.Surface:
    """Carga una imagen por nombre de archivo (con extension), cacheada."""
    if name not in _image_cache:
        path = os.path.join(IMAGES_DIR, name)
        surf = pygame.image.load(path)
        if surf.get_alpha() is not None or surf.get_flags() & pygame.SRCALPHA:
            surf = surf.convert_alpha()
        else:
            surf = surf.convert()
        _image_cache[name] = surf
    return _image_cache[name]


def image_exists(name: str) -> bool:
    return os.path.isfile(os.path.join(IMAGES_DIR, name))


def load_sound(name: str) -> pygame.mixer.Sound | None:
    """Carga un sonido por nombre de archivo, cacheado. Devuelve None
    si no existe o el mixer no esta disponible, sin romper el juego."""
    if name in _sound_cache:
        return _sound_cache[name]
    path = os.path.join(AUDIO_DIR, name)
    if not os.path.isfile(path):
        return None
    try:
        snd = pygame.mixer.Sound(path)
        _sound_cache[name] = snd
        return snd
    except Exception:
        return None


def clear_cache():
    _image_cache.clear()
    _sound_cache.clear()
