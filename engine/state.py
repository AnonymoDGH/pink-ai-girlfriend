"""
Estado global del juego: afecto, obsesion, recuerdos, dias, regalos.
Este modulo es puro (sin dependencias de pygame) para que sea facil
de probar de forma aislada con pytest/unittest.
"""
from __future__ import annotations
import random
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

OBSESSION_YANDERE_THRESHOLD = 70
OBSESSION_WARNING_THRESHOLD = 45


@dataclass
class Memory:
    id: int
    day: int
    category: str          # momento | confesion | celos | promesa | miedo | charla
    text: str
    weight: int = 1         # 1-10
    recalled: int = 0

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        return Memory(**d)


@dataclass
class GameState:
    affection: int = 10
    obsession: int = 0
    days_passed: int = 0
    player_name: str = "tú"
    sakura_mode: str = "normal"
    chat_history: list = field(default_factory=list)   # [{"role":.., "content":..}]
    memories: list = field(default_factory=list)        # list[Memory]
    memory_id_counter: int = 0
    last_recall_day: int = -999
    relationship_stage: str = "inicio"
    yandere_event_on_cooldown: bool = False
    gifts_given: list = field(default_factory=list)
    pc_watch_enabled: bool = False
    pc_watch_consent_shown: bool = False
    seen_yandere_reveal: bool = False

    # ------------------------------------------------------------
    # Afecto / obsesion
    # ------------------------------------------------------------
    def mod_affection(self, amount: int):
        self.affection = max(0, min(100, self.affection + amount))
        self.update_sakura_mode()

    def mod_obsession(self, amount: int):
        self.obsession = max(0, min(100, self.obsession + amount))
        self.update_sakura_mode()

    def update_sakura_mode(self):
        if self.obsession >= OBSESSION_YANDERE_THRESHOLD:
            self.sakura_mode = "yandere"
        elif self.affection >= 60 and self.obsession < OBSESSION_WARNING_THRESHOLD:
            self.sakura_mode = "happy"
        elif self.affection >= 30:
            self.sakura_mode = "blush"
        else:
            self.sakura_mode = "normal"

    def update_relationship_stage(self):
        if self.obsession >= OBSESSION_YANDERE_THRESHOLD:
            self.relationship_stage = "crisis"
        elif self.obsession >= OBSESSION_WARNING_THRESHOLD:
            self.relationship_stage = "tensa"
        elif self.affection >= 70 and self.obsession < 25:
            self.relationship_stage = "estable"
        elif self.days_passed > 1 and self.relationship_stage in ("crisis", "tensa"):
            self.relationship_stage = "reconciliacion"
        else:
            self.relationship_stage = "inicio"

    # ------------------------------------------------------------
    # Recuerdos
    # ------------------------------------------------------------
    def add_memory(self, category: str, text: str, weight: int = 1, day: Optional[int] = None) -> Memory:
        self.memory_id_counter += 1
        mem = Memory(
            id=self.memory_id_counter,
            day=day if day is not None else self.days_passed,
            category=category,
            text=text,
            weight=max(1, min(10, weight)),
        )
        self.memories.append(mem)

        # Poda: nunca borrar recuerdos de peso >= 5, pero limitar los triviales a 300
        low_weight = [m for m in self.memories if m.weight < 5]
        if len(low_weight) > 300:
            low_weight.sort(key=lambda m: (m.weight, -m.day))
            to_remove_ids = {m.id for m in low_weight[: len(low_weight) - 300]}
            self.memories = [m for m in self.memories if m.id not in to_remove_ids]
        return mem

    def remember_from_message(self, user_message: str):
        msg = user_message.lower().strip()
        if len(msg) < 3:
            return None

        if any(w in msg for w in ["prometo", "promesa", "te prometo", "juro"]):
            return self.add_memory("promesa", f'Me prometiste: "{user_message}"', weight=8)
        if any(w in msg for w in ["otra chica", "otro chico", "ex", "mi amiga", "mi amigo", "salí con"]):
            self.mod_obsession(5)
            return self.add_memory("celos", f'Mencionaste algo sobre otra persona: "{user_message}"', weight=7)
        if any(w in msg for w in ["tengo miedo", "me siento solo", "me siento sola", "estoy triste", "no me quiero"]):
            return self.add_memory("confesion", f'Me confesaste algo vulnerable: "{user_message}"', weight=6)
        if any(w in msg for w in ["te amo", "te quiero", "eres hermosa", "eres perfecta", "me encantas"]):
            return self.add_memory("confesion", f'Me dijiste algo muy dulce: "{user_message}"', weight=6)
        return self.add_memory("charla", user_message, weight=2)

    def top_memories_for_prompt(self, n: int = 6):
        if not self.memories:
            return []
        by_weight = sorted(self.memories, key=lambda m: (-m.weight, -m.day))
        important = by_weight[: max(1, n - 2)]
        recent = sorted(self.memories, key=lambda m: -m.day)[:3]
        old_pool = [m for m in self.memories if m not in important]
        old_one = [random.choice(old_pool)] if old_pool else []

        combined = []
        seen_ids = set()
        for m in important + recent + old_one:
            if m.id not in seen_ids:
                combined.append(m)
                seen_ids.add(m.id)
            if len(combined) >= n:
                break
        return combined

    def memories_prompt_block(self) -> str:
        selected = self.top_memories_for_prompt()
        if not selected:
            return ""
        lines = ["Recuerdos importantes que tienes de tu relación con el jugador "
                 "(puedes mencionarlos de forma natural si viene al caso, no los recites como lista):"]
        for m in selected:
            lines.append(f"- (día {m.day}, {m.category}) {m.text}")
        return "\n".join(lines)

    def maybe_spontaneous_recall(self) -> Optional[Memory]:
        if self.days_passed - self.last_recall_day < 2:
            return None
        candidates = [m for m in self.memories if m.weight >= 5 and m.day < self.days_passed]
        if not candidates:
            return None
        if random.random() > 0.35:
            return None
        chosen = random.choice(candidates)
        chosen.recalled += 1
        self.last_recall_day = self.days_passed
        return chosen

    # ------------------------------------------------------------
    # Guardado / carga
    # ------------------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        d["memories"] = [m if isinstance(m, dict) else asdict(m) for m in self.memories]
        return d

    @staticmethod
    def from_dict(d: dict) -> "GameState":
        d = dict(d)
        mems = [Memory.from_dict(m) for m in d.get("memories", [])]
        d["memories"] = mems
        return GameState(**d)

    def save_to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_from_file(path: str) -> "GameState":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return GameState.from_dict(d)
