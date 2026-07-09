import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()
pygame.display.set_mode((200, 200))

from engine.sprite_anim import SakuraSprite, ALL_EXPRESSIONS, SHAKE_MODES
from engine.assets import image_exists


def test_all_modes_have_valid_images():
    sprite = SakuraSprite((400, 600))
    missing = []
    for mode in sorted(ALL_EXPRESSIONS):
        sprite.set_mode(mode)
        # _image_name es interno pero podemos probar get_surface_and_pos
        try:
            img, pos = sprite.get_surface_and_pos()
            assert img.get_width() > 0 and img.get_height() > 0
        except Exception as e:
            missing.append((mode, e))
    assert not missing, f"Faltan imágenes o fallaron: {missing}"
    print(f"OK: all {len(ALL_EXPRESSIONS)} emotional modes render a valid image")


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


# --- Tests nuevos: blink fue ELIMINADO intencionalmente ---
# El parpadeo automático causaba que la expresión real desapareciera
# y se reemplazara por sakura_blink.png (que no coincidía con la emoción).
# Ahora verificamos que NUNCA ocurra un blink espurio.

def test_blinking_never_triggers_because_removed():
    """El parpadeo fue removido: verificar que no hay atributos de blink
    y que la imagen nunca cambia a 'blink' espontáneamente."""
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("normal")
    # No debe existir atributo _is_blinking
    assert not hasattr(sprite, "_is_blinking"), "blink fue removido, no debe existir _is_blinking"
    # Simular 20 segundos y asegurar que la imagen siempre es la correcta
    from engine.sprite_anim import MODE_TO_IMAGE_STEM
    for _ in range(600):
        sprite.update(1/30)
        img_name = sprite._image_name()
        assert "blink" not in img_name, f"¡blink apareció! imagen={img_name}"
        # debe seguir siendo neutral/normal
        expected_stem = MODE_TO_IMAGE_STEM.get("normal", "normal")
        assert expected_stem in img_name
    print("OK: blinking removido correctamente, jamás aparece imagen blink")


def test_happy_mode_never_blinks():
    # Compatibilidad con test antiguo: happy nunca debe parpadear
    # (ahora NINGÚN modo parpadea)
    sprite = SakuraSprite((400, 600))
    sprite.set_mode("happy")
    for _ in range(200):
        sprite.update(1/30)
        assert "blink" not in sprite._image_name()
    print("OK: 'happy' mode never triggers blink (blink system removed)")


def test_mode_switch_keeps_correct_image():
    sprite = SakuraSprite((400, 600))
    for mode in ["normal", "happy", "angry", "crying", "laughing", "yandere"]:
        if mode not in ALL_EXPRESSIONS:
            continue
        sprite.set_mode(mode)
        img_name = sprite._image_name()
        assert "blink" not in img_name, f"mode {mode} produjo blink inesperado"
        assert sprite.mode == mode
    print("OK: switching modes keeps correct image, no blink interference")


def test_all_50_expressions_supported():
    assert len(ALL_EXPRESSIONS) >= 50, f"Se esperaban al menos 50 expresiones, hay {len(ALL_EXPRESSIONS)}"
    print(f"OK: {len(ALL_EXPRESSIONS)} expresiones soportadas (>=50)")


if __name__ == "__main__":
    test_all_modes_have_valid_images()
    test_sway_produces_movement_over_time()
    test_yandere_shake_produces_horizontal_jitter()
    test_blinking_never_triggers_because_removed()
    test_happy_mode_never_blinks()
    test_mode_switch_keeps_correct_image()
    test_all_50_expressions_supported()
    print("\n=== ALL SPRITE_ANIM TESTS PASSED ===")
