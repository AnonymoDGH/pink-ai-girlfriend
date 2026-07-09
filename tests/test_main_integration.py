"""
Prueba de integracion end-to-end para la nueva arquitectura dirigida
por IA: instancia el juego real (Game) con el driver de video/audio
'dummy' de SDL, mockeando las llamadas de red a la IA (para que las
pruebas sean rapidas y no gasten cuota de API real), y simula input
de teclado/mouse para recorrer varias interacciones.
"""
import os
import sys
import json
import queue

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
# evitamos que un .env real con API keys reales dispare llamadas de
# red de verdad durante los tests: forzamos que no haya keys, y
# mockeamos ai_director.direct_next_line directamente.
for var in ("NVIDIA_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(var, None)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame

TEST_SAVE_PATH = os.path.join(os.path.dirname(__file__), "..", "savegame.json")
if os.path.isfile(TEST_SAVE_PATH):
    os.remove(TEST_SAVE_PATH)

import main as main_module
from engine import ai_director


def _install_fake_director(monkeypatch_dialogue="Hola, esto es una prueba.",
                            expression="happy", background=None, replies=None):
    """Reemplaza ai_director.direct_next_line por una version instantanea
    y sin red, para que los tests de integracion sean deterministas y
    rapidos."""
    replies = replies or ["Opción uno", "Opción dos", "Opción tres"]
    original = ai_director.direct_next_line

    def fake_direct_next_line(game_state, player_message, action_context="", pc_watch_block="", http_post=None):
        return ai_director.DirectorResponse(
            dialogue=monkeypatch_dialogue,
            expression=expression,
            background=background,
            suggested_replies=replies,
            provider_used="fake_test_provider",
        )

    ai_director.direct_next_line = fake_direct_next_line
    return original


def _restore_director(original):
    ai_director.direct_next_line = original


def _wait_for_ai(game, max_polls=200):
    """Como la llamada corre en un hilo, hacemos polling manual del
    resultado (igual que el loop principal) hasta que deje de estar
    en modo 'waiting_ai'."""
    for _ in range(max_polls):
        game._poll_ai_result()
        if game.mode != "waiting_ai":
            return True
        import time
        time.sleep(0.01)
    return False


def test_game_boots_and_shows_first_ai_line():
    original = _install_fake_director()
    try:
        game = main_module.Game(fullscreen=False)
        assert game.mode == "waiting_ai"
        ok = _wait_for_ai(game)
        assert ok, "la respuesta de la IA (mockeada) deberia llegar rapido"
        assert game.mode == "showing_reply"
        assert game.dialogue_box.full_text == "Hola, esto es una prueba."
        assert len(game.reply_buttons.options) == 3
        print("OK: el juego arranca, pide la primera linea a la IA (mockeada) y la muestra")
        return game
    finally:
        _restore_director(original)


def test_selecting_suggested_reply_triggers_next_ai_call():
    original = _install_fake_director(monkeypatch_dialogue="Primera línea")
    try:
        game = main_module.Game(fullscreen=False)
        _wait_for_ai(game)
        game.dialogue_box.skip_to_end()

        # cambiar el mock para la siguiente respuesta
        def second_response(game_state, player_message, action_context="", pc_watch_block="", http_post=None):
            assert player_message == game.reply_buttons.options[0]
            return ai_director.DirectorResponse(
                dialogue="Segunda línea, respondiendo a tu elección.",
                expression="blush", background=None,
                suggested_replies=["A", "B", "C"], provider_used="fake",
            )
        ai_director.direct_next_line = second_response

        chosen_text = game.reply_buttons.options[0]
        game._submit_player_choice(chosen_text)
        assert game.mode == "waiting_ai"
        ok = _wait_for_ai(game)
        assert ok
        assert game.dialogue_box.full_text == "Segunda línea, respondiendo a tu elección."
        assert game.sprite.mode == "blush"
        print("OK: elegir una respuesta sugerida dispara la siguiente linea de la IA correctamente")
    finally:
        _restore_director(original)


def test_free_text_input_flow():
    original = _install_fake_director()
    try:
        game = main_module.Game(fullscreen=False)
        _wait_for_ai(game)
        game.dialogue_box.skip_to_end()

        # simular click en "escribir mi propia respuesta"
        game.showing_free_text_input = True
        game.text_input.active = True

        for ch in "hola, como estas":
            ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode=ch, mod=0)
            game.text_input.handle_event(ev)

        def free_text_response(game_state, player_message, action_context="", pc_watch_block="", http_post=None):
            assert player_message == "hola, como estas"
            return ai_director.DirectorResponse(
                dialogue="Respondiendo a tu texto libre.",
                expression="happy", background=None,
                suggested_replies=["X", "Y"], provider_used="fake",
            )
        ai_director.direct_next_line = free_text_response

        enter_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r", mod=0)
        game.text_input.handle_event(enter_ev)
        submitted = game.text_input.consume_submission()
        assert submitted == "hola, como estas"
        game._submit_player_choice(submitted)

        ok = _wait_for_ai(game)
        assert ok
        assert game.dialogue_box.full_text == "Respondiendo a tu texto libre."
        print("OK: flujo de texto libre funciona correctamente end-to-end")
    finally:
        _restore_director(original)


def test_stats_overlay_toggle():
    original = _install_fake_director()
    try:
        game = main_module.Game(fullscreen=False)
        _wait_for_ai(game)
        game.dialogue_box.skip_to_end()

        tab_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0)
        game.handle_event(tab_event)
        assert game.mode == "stats_overlay"
        game.draw()  # no debe crashear

        game.handle_event(tab_event)
        assert game.mode == "showing_reply"
        print("OK: stats overlay abre y cierra sin crashear")
    finally:
        _restore_director(original)


def test_save_and_reload_state():
    original = _install_fake_director()
    try:
        game = main_module.Game(fullscreen=False)
        _wait_for_ai(game)
        game.game_state.mod_affection(20)
        game.save_game()
        assert os.path.isfile(main_module.SAVE_PATH)

        game2 = main_module.Game(fullscreen=False)
        _wait_for_ai(game2)
        assert game2.game_state.affection == game.game_state.affection
        print("OK: guardado y recarga de partida funciona")
        os.remove(main_module.SAVE_PATH)
    finally:
        _restore_director(original)


def test_draw_does_not_crash_across_many_frames():
    original = _install_fake_director()
    try:
        game = main_module.Game(fullscreen=False)
        _wait_for_ai(game)
        for _ in range(120):
            game.update(1 / 60)
            game.draw()
        print("OK: 120 frames dibujados sin crashear")
    finally:
        _restore_director(original)


def test_fullscreen_mode_boots_without_crash():
    """Confirma que el modo pantalla completa (el default real del
    juego) tambien inicializa sin errores bajo el driver dummy."""
    original = _install_fake_director()
    try:
        game = main_module.Game(fullscreen=True)
        _wait_for_ai(game)
        game.draw()
        assert game.screen_w > 0 and game.screen_h > 0
        print(f"OK: modo pantalla completa arranca sin crash ({game.screen_w}x{game.screen_h})")
    finally:
        _restore_director(original)


if __name__ == "__main__":
    test_game_boots_and_shows_first_ai_line()
    test_selecting_suggested_reply_triggers_next_ai_call()
    test_free_text_input_flow()
    test_stats_overlay_toggle()
    test_save_and_reload_state()
    test_draw_does_not_crash_across_many_frames()
    test_fullscreen_mode_boots_without_crash()
    print("\n=== ALL MAIN INTEGRATION TESTS PASSED ===")
