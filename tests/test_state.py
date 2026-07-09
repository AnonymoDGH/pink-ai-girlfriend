import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.state import GameState, Memory


def test_affection_obsession_bounds():
    gs = GameState()
    gs.mod_affection(200)
    assert gs.affection == 100
    gs.mod_affection(-500)
    assert gs.affection == 0
    gs.mod_obsession(1000)
    assert gs.obsession == 100
    print("OK: bounds respected")


def test_mode_transitions():
    gs = GameState()
    gs.affection, gs.obsession = 10, 0
    gs.update_sakura_mode()
    assert gs.sakura_mode == "normal"

    gs.affection, gs.obsession = 65, 10
    gs.update_sakura_mode()
    assert gs.sakura_mode == "happy"

    gs.affection, gs.obsession = 40, 20
    gs.update_sakura_mode()
    assert gs.sakura_mode == "blush"

    gs.affection, gs.obsession = 50, 75
    gs.update_sakura_mode()
    assert gs.sakura_mode == "yandere"
    print("OK: mode transitions")


def test_memory_categorization():
    gs = GameState()
    gs.remember_from_message("te prometo que nunca te voy a dejar")
    gs.remember_from_message("hoy vi a mi ex en la calle")
    gs.remember_from_message("tengo miedo de estar solo")
    gs.remember_from_message("te amo muchisimo")
    gs.remember_from_message("hola como estas")
    cats = [m.category for m in gs.memories]
    assert cats == ["promesa", "celos", "confesion", "confesion", "charla"], cats
    print("OK: memory categorization", cats)


def test_memory_pruning_caps_low_weight():
    gs = GameState()
    for i in range(350):
        gs.add_memory("charla", f"mensaje {i}", weight=2)
    assert len(gs.memories) <= 300
    print("OK: pruning capped at", len(gs.memories))


def test_high_weight_memory_never_pruned():
    gs = GameState()
    for i in range(310):
        gs.add_memory("charla", f"msg {i}", weight=2)
    gs.add_memory("promesa", "promesa importante", weight=9)
    assert any(m.text == "promesa importante" for m in gs.memories)
    print("OK: high weight memory survived, total =", len(gs.memories))


def test_top_memories_for_prompt():
    gs = GameState()
    gs.add_memory("promesa", "nunca te dejare", weight=9, day=1)
    gs.add_memory("celos", "vio a su ex", weight=7, day=2)
    gs.add_memory("charla", "hablamos del clima", weight=2, day=3)
    gs.add_memory("confesion", "confeso que tiene miedo", weight=6, day=4)
    top = gs.top_memories_for_prompt(4)
    assert len(top) <= 4
    assert any(m.category == "promesa" for m in top)
    print("OK: top memories selection", [(m.category, m.weight) for m in top])


def test_save_and_load_roundtrip():
    gs = GameState()
    gs.mod_affection(42)
    gs.mod_obsession(13)
    gs.days_passed = 7
    gs.add_memory("promesa", "una promesa importante", weight=9)
    gs.gifts_given.append("flores")

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "save.json")
        gs.save_to_file(path)
        loaded = GameState.load_from_file(path)

    assert loaded.affection == gs.affection
    assert loaded.obsession == gs.obsession
    assert loaded.days_passed == 7
    assert loaded.gifts_given == ["flores"]
    assert len(loaded.memories) == 1
    assert isinstance(loaded.memories[0], Memory)
    assert loaded.memories[0].text == "una promesa importante"
    print("OK: save/load roundtrip works")


def test_relationship_stage_cycles():
    gs = GameState()
    gs.affection, gs.obsession = 10, 0
    gs.days_passed = 1
    gs.update_relationship_stage()
    assert gs.relationship_stage == "inicio"

    gs.obsession = 80
    gs.update_relationship_stage()
    assert gs.relationship_stage == "crisis"

    gs.obsession = 10
    gs.affection = 75
    gs.days_passed = 2
    gs.update_relationship_stage()
    # tras estar en crisis y bajar, entra en reconciliacion o estable segun umbral
    assert gs.relationship_stage in ("estable", "reconciliacion")
    print("OK: relationship stage cycles, ended at", gs.relationship_stage)


if __name__ == "__main__":
    test_affection_obsession_bounds()
    test_mode_transitions()
    test_memory_categorization()
    test_memory_pruning_caps_low_weight()
    test_high_weight_memory_never_pruned()
    test_top_memories_for_prompt()
    test_save_and_load_roundtrip()
    test_relationship_stage_cycles()
    print("\n=== ALL STATE TESTS PASSED ===")
