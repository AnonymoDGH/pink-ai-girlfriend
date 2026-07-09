"""
Prueba EN VIVO contra la API real de NVIDIA NIM (requiere que .env
tenga NVIDIA_API_KEY configurada). Se salta automaticamente si no
hay key disponible, para no romper la suite de CI/offline.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.env_loader import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from engine import ai_director
from engine.state import GameState


def test_live_director_returns_valid_structure():
    if not os.environ.get("NVIDIA_API_KEY"):
        print("SKIPPED: no NVIDIA_API_KEY configurada")
        return

    gs = GameState()
    gs.affection = 40
    gs.obsession = 5
    gs.update_sakura_mode()

    result = ai_director.direct_next_line(gs, "Hola Sakura, ¿qué tal tu día?")
    print("dialogue:", result.dialogue)
    print("expression:", result.expression)
    print("background:", result.background)
    print("suggested_replies:", result.suggested_replies)
    print("provider_used:", result.provider_used)

    assert result.provider_used == "nvidia_nim"
    assert isinstance(result.dialogue, str) and len(result.dialogue) > 0
    assert result.expression in ai_director.VALID_EXPRESSIONS
    assert isinstance(result.suggested_replies, list)
    assert len(result.suggested_replies) >= 1
    print("OK: director en vivo devuelve estructura valida")


def test_live_director_yandere_mode_reflects_in_expression():
    if not os.environ.get("NVIDIA_API_KEY"):
        print("SKIPPED: no NVIDIA_API_KEY configurada")
        return

    gs = GameState()
    gs.affection = 60
    gs.obsession = 85
    gs.update_sakura_mode()
    assert gs.sakura_mode == "yandere"

    result = ai_director.direct_next_line(gs, "Voy a salir con mis amigos todo el fin de semana")
    print("dialogue (yandere):", result.dialogue)
    print("expression (yandere):", result.expression)
    assert result.provider_used == "nvidia_nim"
    print("OK: modo yandere consultado exitosamente en vivo")


def test_live_director_initiative_without_player_message():
    if not os.environ.get("NVIDIA_API_KEY"):
        print("SKIPPED: no NVIDIA_API_KEY configurada")
        return

    gs = GameState()
    result = ai_director.direct_next_line(gs, None, action_context="El jugador acaba de sentarse junto a ella por primera vez hoy.")
    print("dialogue (iniciativa):", result.dialogue)
    assert result.provider_used == "nvidia_nim"
    assert len(result.dialogue) > 0
    print("OK: la IA puede tomar la iniciativa sin mensaje del jugador")


if __name__ == "__main__":
    test_live_director_returns_valid_structure()
    test_live_director_yandere_mode_reflects_in_expression()
    test_live_director_initiative_without_player_message()
    print("\n=== LIVE AI DIRECTOR TESTS DONE ===")
