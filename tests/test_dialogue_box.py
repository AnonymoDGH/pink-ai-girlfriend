import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()
pygame.display.set_mode((200, 200))
pygame.mixer.init()

from engine.dialogue_box import DialogueBox


def make_box():
    font = pygame.font.SysFont(None, 20)
    name_font = pygame.font.SysFont(None, 22)
    rect = pygame.Rect(0, 150, 800, 150)
    return DialogueBox(font, name_font, rect, chars_per_second=50)


def test_text_reveals_progressively():
    box = make_box()
    box.set_text("Sakura", "Hola, esto es una prueba de texto largo para el dialogo.")
    assert box.visible_chars == 0
    assert not box.is_finished()

    # simular 0.5 segundos a 50 chars/seg -> deberian revelarse ~25 caracteres
    box.update(0.5)
    assert 20 <= box.visible_chars <= 30, box.visible_chars
    assert not box.is_finished()
    print("OK: text reveals progressively, visible_chars =", box.visible_chars)


def test_text_completes_eventually():
    box = make_box()
    text = "Texto corto."
    box.set_text("Sakura", text)
    for _ in range(50):
        box.update(0.1)
        if box.is_finished():
            break
    assert box.is_finished()
    assert box.visible_chars == len(text)
    print("OK: text completes eventually")


def test_skip_to_end():
    box = make_box()
    box.set_text("Sakura", "Un texto que sera saltado inmediatamente.")
    box.skip_to_end()
    assert box.is_finished()
    assert box.visible_chars == len(box.full_text)
    print("OK: skip_to_end works")


def test_empty_text_is_immediately_finished():
    box = make_box()
    box.set_text("Sakura", "")
    assert box.is_finished()
    print("OK: empty text is finished immediately")


def test_draw_does_not_crash():
    box = make_box()
    box.set_text("Sakura", "Probando que el render no falle, con texto largo que ocupa varias lineas de ancho limitado.")
    surface = pygame.Surface((800, 600))
    for _ in range(20):
        box.update(0.05)
        box.draw(surface)  # no debe lanzar excepcion
    print("OK: draw() runs without crashing across many frames")


if __name__ == "__main__":
    test_text_reveals_progressively()
    test_text_completes_eventually()
    test_skip_to_end()
    test_empty_text_is_immediately_finished()
    test_draw_does_not_crash()
    print("\n=== ALL DIALOGUE_BOX TESTS PASSED ===")
