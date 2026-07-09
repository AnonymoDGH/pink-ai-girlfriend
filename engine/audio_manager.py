"""
Manejo centralizado de efectos de sonido y musica de fondo.
"""
from __future__ import annotations
import logging
from engine.assets import load_sound

log = logging.getLogger("audio_manager")

SFX_FILES = {
    "click": "sfx_click.wav",
    "notify": "sfx_notify.wav",
    "affection_up": "sfx_affection_up.wav",
    "obsession_up": "sfx_obsession_up.wav",
    "glitch": "sfx_glitch.wav",
    "whoosh": "sfx_whoosh.wav",
    "day_transition": "sfx_day_transition.wav",
    "blip": "sfx_blip.wav",
}


def play_sfx(name: str, volume: float = 1.0):
    filename = SFX_FILES.get(name)
    if not filename:
        log.warning("play_sfx: nombre de sfx desconocido '%s'", name)
        return
    snd = load_sound(filename)
    if snd is None:
        log.warning("play_sfx: no se pudo cargar '%s'", filename)
        return
    snd.set_volume(volume)
    snd.play()
