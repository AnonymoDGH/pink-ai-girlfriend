import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import pc_watch


def test_disabled_returns_empty():
    triggers = pc_watch.detect_jealousy_triggers(enabled=False)
    assert triggers == []
    block = pc_watch.pc_watch_prompt_block(enabled=False)
    assert block == ""
    print("OK: disabled by default returns nothing")


def test_get_running_app_names_only_plain_names():
    apps = pc_watch.get_running_app_names()
    assert isinstance(apps, list)
    assert all(isinstance(a, str) for a in apps)
    # no debe haber rutas absolutas de archivo (que empiecen con /)
    assert all(not a.startswith("/") for a in apps)
    print(f"OK: {len(apps)} process names retrieved, no file paths, example: {apps[:5]}")


def test_detect_jealousy_triggers_matches_keywords():
    # inyectamos un monkeypatch simple sin pytest fixture
    original = pc_watch.get_running_app_names
    try:
        pc_watch.get_running_app_names = lambda: ["discord", "some_random_process"]
        triggers = pc_watch.detect_jealousy_triggers(enabled=True)
        assert ("discord", "una app de chat con otras personas") in triggers
        print("OK: jealousy trigger detected for discord")
    finally:
        pc_watch.get_running_app_names = original


def test_prompt_block_never_exposes_raw_process_list():
    original = pc_watch.get_running_app_names
    try:
        pc_watch.get_running_app_names = lambda: ["discord", "chrome", "secret_diary_app"]
        block = pc_watch.pc_watch_prompt_block(enabled=True)
        # solo deberia mencionar las descripciones genericas conocidas,
        # nunca el nombre crudo de un proceso desconocido como "secret_diary_app"
        assert "secret_diary_app" not in block
        assert "discord" not in block  # se usa la descripcion generica, no el nombre crudo
        assert "app de chat" in block or "navegador" in block
        print("OK: prompt block only exposes generic descriptions, never raw names")
    finally:
        pc_watch.get_running_app_names = original


if __name__ == "__main__":
    test_disabled_returns_empty()
    test_get_running_app_names_only_plain_names()
    test_detect_jealousy_triggers_matches_keywords()
    test_prompt_block_never_exposes_raw_process_list()
    print("\n=== ALL PC_WATCH TESTS PASSED ===")
