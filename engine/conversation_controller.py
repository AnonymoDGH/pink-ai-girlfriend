"""
Controlador de la conversacion dirigida por IA. A diferencia de un
chat de mensajes, aqui la IA actua como "directora" del personaje:
decide el dialogo, la expresion, si cambia el fondo, y que opciones
de respuesta ofrecerle al jugador (ademas de la opcion de escribir
libremente). Este modulo es puro (sin pygame) para poder testearlo
facilmente; el hilo/threading para no bloquear la UI se maneja en
main.py.
"""
from __future__ import annotations
import logging
from engine import ai_director
from engine import pc_watch

log = logging.getLogger("conversation_controller")

TURNS_PER_DAY = 8  # cada cuantos turnos de conversacion se considera que paso "un dia"


class ConversationController:
    def __init__(self, game_state):
        self.game_state = game_state
        self.current: ai_director.DirectorResponse | None = None
        self.turns_this_day = 0
        self.pending_yandere_check = True

    def _pc_watch_block(self) -> str:
        return pc_watch.pc_watch_prompt_block(self.game_state.pc_watch_enabled)

    def _apply_sentiment_nudge(self, player_text: str | None):
        """Pequeños ajustes de stats segun palabras clave del mensaje
        del jugador, igual que antes, para que las decisiones del
        jugador sigan influyendo el afecto/obsesion de forma directa
        (ademas de lo que la IA decida narrativamente)."""
        if not player_text:
            return
        msg = player_text.lower()
        if any(w in msg for w in ("odio", "molesta", "aburrida", "fea")):
            self.game_state.mod_affection(-4)
            self.game_state.mod_obsession(3)
        elif any(w in msg for w in ("amo", "linda", "hermosa", "quiero", "gracias")):
            self.game_state.mod_affection(4)

    def _maybe_advance_day(self) -> str:
        """Cada TURNS_PER_DAY turnos, avanza el contador de dias y
        revisa si hay un recuerdo espontaneo para inyectar como
        contexto. Devuelve un string de contexto extra (o "")."""
        self.turns_this_day += 1
        if self.turns_this_day < TURNS_PER_DAY:
            return ""
        self.turns_this_day = 0
        self.game_state.days_passed += 1
        self.game_state.update_relationship_stage()

        memory = self.game_state.maybe_spontaneous_recall()
        if memory:
            return (
                f"Ha pasado un tiempo (día {self.game_state.days_passed} de la relación). "
                f"Se te viene a la mente este recuerdo, y decides sacarlo a relucir tu misma "
                f"de forma natural sin que el jugador pregunte: \"{memory.text}\" "
                f"(categoría: {memory.category})."
            )
        return f"Ha pasado un tiempo (día {self.game_state.days_passed} de la relación)."

    def start(self, opening_context: str = "") -> ai_director.DirectorResponse:
        """Genera la primera linea de la conversacion (la IA toma la
        iniciativa, sin mensaje del jugador todavia)."""
        result = ai_director.direct_next_line(
            self.game_state, None,
            action_context=opening_context,
            pc_watch_block=self._pc_watch_block(),
        )
        self.current = result
        return result

    def submit_player_line(self, player_text: str, extra_context: str = "") -> ai_director.DirectorResponse:
        """Procesa una linea del jugador (elegida de las sugerencias o
        escrita libremente) y devuelve la siguiente respuesta dirigida
        por la IA."""
        self._apply_sentiment_nudge(player_text)
        self.game_state.remember_from_message(player_text)

        day_context = self._maybe_advance_day()
        full_context = " ".join(c for c in (extra_context, day_context) if c)

        result = ai_director.direct_next_line(
            self.game_state, player_text,
            action_context=full_context,
            pc_watch_block=self._pc_watch_block(),
        )
        self.current = result
        return result

    def inject_event_context(self, context: str) -> ai_director.DirectorResponse:
        """Para cuando algo pasa SIN que el jugador escriba nada (ej.
        termino de dar un regalo, o se disparo la crisis de obsesion):
        le pide a la IA que reaccione a ese evento por su cuenta."""
        result = ai_director.direct_next_line(
            self.game_state, None,
            action_context=context,
            pc_watch_block=self._pc_watch_block(),
        )
        self.current = result
        return result

    def check_yandere_trigger(self) -> bool:
        """Devuelve True si corresponde disparar el evento de crisis de
        obsesion (una vez por 'episodio': se resetea el cooldown cuando
        la obsesion vuelve a bajar del umbral)."""
        gs = self.game_state
        if gs.sakura_mode == "yandere" and not gs.yandere_event_on_cooldown:
            gs.yandere_event_on_cooldown = True
            return True
        if gs.sakura_mode != "yandere":
            gs.yandere_event_on_cooldown = False
        return False
