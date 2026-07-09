import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()
pygame.display.set_mode((200, 200))

from engine.sprite_anim import SakuraSprite, BLINK_TIMING, SHAKE_MODES


def test_all_modes_have_valid_images():
    sprite = SakuraSprite((400, 600))
    for mode in BLINK_TIMING:
        sprite.set_mode(mode)
        img, pos = sprite.get_surface_and_pos()
        assert img.get_width() > 0 and img.get_height() > 0
    print("OK: all emotional modes render a valid image")


def test_sway_produces_movement_over_time():
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("normal")
    positions = []
    for _ in range(60):
        sprite.update(1/30)
        _, pos = sprite.get_surface_and_pos()
        positions.append(pos)
    ys = [p[1] for p in positions]
    assert max(ys) != min(ys), "el balanceo deberia producir variacion vertical"
    print("OK: idle sway produces vertical movement over time, range=", max(ys) - min(ys))


def test_yandere_shake_produces_horizontal_jitter():
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("yandere")
    xs = []
    for _ in range(60):
        sprite.update(1/30)
        _, pos = sprite.get_surface_and_pos()
        xs.append(pos[0])
    assert max(xs) != min(xs), "el temblor deberia producir variacion horizontal"
    print("OK: yandere shake produces horizontal jitter, range=", max(xs) - min(xs))


def test_blinking_eventually_triggers():
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("normal")  # normal SI parpadea (close_dur > 0)
    triggered = False
    for _ in range(600):  # hasta 20 segundos simulados
        sprite.update(1/30)
        if sprite._is_blinking:
            triggered = True
            break
    assert triggered, "deberia parpadear en algun momento dentro de 20s simulados"
    print("OK: blinking eventually triggers for 'normal' mode")


def test_happy_mode_never_blinks():
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("happy")  # happy tiene close_dur = 0, no deberia parpadear
    for _ in range(600):
        sprite.update(1/30)
        assert not sprite._is_blinking
    print("OK: 'happy' mode never triggers blink (as designed)")


def test_mode_switch_resets_blink_state():
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("normal")
    sprite._is_blinking = True
    sprite.set_mode("sad")
    assert not sprite._is_blinking
    assert sprite.mode == "sad"
    print("OK: switching modes resets blink state cleanly")


if __name__ == "__main__":
    test_all_modes_have_valid_images()
    test_sway_produces_movement_over_time()
    test_yandere_shake_produces_horizontal_jitter()
    test_blinking_eventually_triggers()
    test_happy_mode_never_blinks()
    test_mode_switch_resets_blink_state()
    print("\n=== ALL SPRITE_ANIM TESTS PASSED ===")
