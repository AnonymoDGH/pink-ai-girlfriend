import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.conversation_controller import ConversationController, TURNS_PER_DAY
from engine.state import GameState
from engine import ai_director


def fake_http_post_factory(dialogue="Hola", expression="happy", background=None, replies=None):
    replies = replies or ["A", "B", "C"]
    def _fake(url, payload_bytes, headers):
        return json.dumps({
            "dialogue": dialogue,
            "expression": expression,
            "background": background,
            "suggested_replies": replies,
        })
    return _fake


def test_start_takes_initiative_without_player_text(monkeypatch):
    gs = GameState()
    ctrl = ConversationController(gs)

    monkeypatch.setenv("NVIDIA_API_KEY", "fake")
    fake_post = fake_http_post_factory(dialogue="¡Hola! Que bueno verte.")

    # inyectamos http_post via monkeypatch de la funcion interna
    orig = ai_director._call_provider
    def patched(provider, messages, http_post=None):
        return orig(provider, messages, http_post=fake_post)
    ai_director._call_provider = patched
    try:
        result = ctrl.start()
        assert result.dialogue == "¡Hola! Que bueno verte."
        assert result.expression == "happy"
    finally:
        ai_director._call_provider = orig
    print("OK: start() toma la iniciativa sin texto del jugador")


def test_submit_player_line_updates_memory_and_stats(monkeypatch):
    gs = GameState()
    ctrl = ConversationController(gs)

    fake_post = fake_http_post_factory(dialogue="Yo también te quiero.", expression="blush")
    orig = ai_director._call_provider
    def patched(provider, messages, http_post=None):
        return orig(provider, messages, http_post=fake_post)
    ai_director._call_provider = patched
    monkeypatch.setenv("NVIDIA_API_KEY", "fake")
    try:
        result = ctrl.submit_player_line("te amo mucho sakura")
    finally:
        ai_director._call_provider = orig

    assert result.dialogue == "Yo también te quiero."
    assert gs.affection > 10  # deberia haber subido por "te amo"
    assert len(gs.memories) == 1
    assert gs.memories[0].category == "confesion"
    print("OK: submit_player_line actualiza memoria y stats correctamente")


def test_day_advances_after_n_turns(monkeypatch):
    gs = GameState()
    ctrl = ConversationController(gs)

    fake_post = fake_http_post_factory()
    orig = ai_director._call_provider
    def patched(provider, messages, http_post=None):
        return orig(provider, messages, http_post=fake_post)
    ai_director._call_provider = patched
    monkeypatch.setenv("NVIDIA_API_KEY", "fake")
    try:
        for i in range(TURNS_PER_DAY):
            ctrl.submit_player_line(f"mensaje numero {i}")
    finally:
        ai_director._call_provider = orig

    assert gs.days_passed == 1, gs.days_passed
    print("OK: el dia avanza automaticamente tras TURNS_PER_DAY turnos")


def test_yandere_trigger_cooldown_cycle():
    gs = GameState()
    ctrl = ConversationController(gs)

    gs.obsession = 80
    gs.update_sakura_mode()
    assert ctrl.check_yandere_trigger() is True
    # segunda llamada inmediata no deberia volver a disparar (cooldown activo)
    assert ctrl.check_yandere_trigger() is False

    # una vez que baja la obsesion, se resetea el cooldown
    gs.obsession = 10
    gs.update_sakura_mode()
    assert ctrl.check_yandere_trigger() is False  # ya no esta en modo yandere, no dispara

    # y si vuelve a subir, puede volver a dispararse
    gs.obsession = 90
    gs.update_sakura_mode()
    assert ctrl.check_yandere_trigger() is True
    print("OK: ciclo de cooldown del evento yandere funciona correctamente")


def test_inject_event_context_does_not_require_player_text(monkeypatch):
    gs = GameState()
    ctrl = ConversationController(gs)
    fake_post = fake_http_post_factory(dialogue="¡Me encantó el regalo!", expression="happy")
    orig = ai_director._call_provider
    def patched(provider, messages, http_post=None):
        return orig(provider, messages, http_post=fake_post)
    ai_director._call_provider = patched
    monkeypatch.setenv("NVIDIA_API_KEY", "fake")
    try:
        result = ctrl.inject_event_context("El jugador le acaba de dar un peluche de regalo.")
    finally:
        ai_director._call_provider = orig
    assert "regalo" in result.dialogue.lower()
    print("OK: inject_event_context genera reaccion sin texto del jugador")


if __name__ == "__main__":
    import types

    class FakeMonkeypatch:
        def __init__(self):
            self._saved = {}
        def setenv(self, k, v):
            self._saved.setdefault(k, os.environ.get(k))
            os.environ[k] = v
        def restore(self):
            for k, v in self._saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    for test_fn in [
        test_start_takes_initiative_without_player_text,
        test_submit_player_line_updates_memory_and_stats,
        test_day_advances_after_n_turns,
    ]:
        mp = FakeMonkeypatch()
        try:
            test_fn(mp)
        finally:
            mp.restore()

    test_yandere_trigger_cooldown_cycle()

    mp = FakeMonkeypatch()
    try:
        test_inject_event_context_does_not_require_player_text(mp)
    finally:
        mp.restore()

    print("\n=== ALL CONVERSATION_CONTROLLER TESTS PASSED ===")
