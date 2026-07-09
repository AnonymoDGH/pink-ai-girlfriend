#!/usr/bin/env python3
"""
Pink AI Girlfriend — motor 100% Python (pygame), sin Ren'Py.

La IA actua como DIRECTORA del personaje de Sakura: decide que dice,
que expresion pone, y si cambia de escenario, en cada turno. El
jugador responde eligiendo una de las opciones sugeridas por la IA,
o escribiendo su propio texto libre. El juego corre en pantalla
completa y nunca "termina": la relacion evoluciona indefinidamente.
"""
from __future__ import annotations
import os
import sys
import logging
import threading
import queue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.env_loader import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

import pygame

from engine.state import GameState
from engine.sprite_anim import SakuraSprite
from engine.dialogue_box import DialogueBox
from engine.ui_widgets import StatsPanel, MemoryDiaryPanel, TextInputBox, SuggestedReplyButtons
from engine.assets import load_image, image_exists
from engine import audio_manager
from engine import ai_director
from engine.conversation_controller import ConversationController

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

FPS = 60
SAVE_PATH = os.path.join(BASE_DIR, "savegame.json")

BACKGROUND_FILES = {
    "classroom": "bg_classroom.png",
    "classroom_dark": "bg_classroom_dark.png",
    "bedroom": "bg_bedroom.png",
    "rooftop": "bg_rooftop.png",
    "cafe": "bg_cafe.png",
    "festival": "bg_festival.png",
    "street": "bg_street.png",
}


class Game:
    def __init__(self, fullscreen: bool = True):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception as e:
            log.warning("No se pudo inicializar el audio: %r", e)

        if fullscreen:
            info = pygame.display.Info()
            self.screen_w, self.screen_h = info.current_w, info.current_h
            self.screen = pygame.display.set_mode((self.screen_w, self.screen_h), pygame.FULLSCREEN)
        else:
            self.screen_w, self.screen_h = 1280, 720
            self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))

        pygame.display.set_caption("Pink AI Girlfriend")
        pygame.mouse.set_visible(True)
        self.clock = pygame.time.Clock()
        self.running = True

        self._init_fonts()

        self.game_state = self._load_or_new_state()
        self.controller = ConversationController(self.game_state)

        self.sprite = SakuraSprite((self.screen_w // 2, self.screen_h - 30))
        self.sprite.set_mode(self.game_state.sakura_mode)
        self.current_background = "classroom"

        dialogue_rect = pygame.Rect(
            int(self.screen_w * 0.04), self.screen_h - int(self.screen_h * 0.24),
            int(self.screen_w * 0.92), int(self.screen_h * 0.16),
        )
        self.dialogue_box = DialogueBox(self.font_dialogue, self.font_name, dialogue_rect,
                                         wrap_width_chars=int(self.screen_w / 16))

        replies_rect = pygame.Rect(
            int(self.screen_w * 0.62), int(self.screen_h * 0.08),
            int(self.screen_w * 0.34), int(self.screen_h * 0.62),
        )
        self.reply_buttons = SuggestedReplyButtons(self.font_menu, replies_rect)

        input_rect = pygame.Rect(
            int(self.screen_w * 0.04), self.screen_h - int(self.screen_h * 0.07),
            int(self.screen_w * 0.92), int(self.screen_h * 0.055),
        )
        self.text_input = TextInputBox(self.font_dialogue, input_rect)

        self.stats_panel = StatsPanel(self.font_small, self.font_title)
        self.memory_panel = MemoryDiaryPanel(self.font_small, self.font_title)

        # mode: "waiting_ai" | "showing_reply" | "typing_free_text" | "stats_overlay" | "memory_overlay"
        self.mode = "waiting_ai"
        self.showing_free_text_input = False

        # Comunicacion con el hilo de red para no congelar la UI mientras
        # se espera la respuesta de la IA.
        self._ai_result_queue: "queue.Queue[ai_director.DirectorResponse]" = queue.Queue()
        self._ai_thread: threading.Thread | None = None
        self._ai_loading = False
        self._loading_dots_timer = 0.0

        self._request_opening_line()

    # ------------------------------------------------------------
    def _init_fonts(self):
        scale = max(0.8, min(1.6, self.screen_h / 720))

        def sz(base):
            return int(base * scale)

        self.font_dialogue = self._load_font(sz(24))
        self.font_name = self._load_font(sz(26), bold=True)
        self.font_menu = self._load_font(sz(20))
        self.font_small = self._load_font(sz(18))
        self.font_title = self._load_font(sz(30), bold=True)

    def _load_font(self, size, bold=False):
        try:
            return pygame.font.SysFont("dejavusans", size, bold=bold)
        except Exception:
            return pygame.font.Font(None, size)

    def _load_or_new_state(self) -> GameState:
        if os.path.isfile(SAVE_PATH):
            try:
                gs = GameState.load_from_file(SAVE_PATH)
                log.info("Partida cargada desde %s", SAVE_PATH)
                return gs
            except Exception as e:
                log.warning("No se pudo cargar la partida guardada (%r), empezando nueva.", e)
        return GameState()

    def save_game(self):
        try:
            self.game_state.save_to_file(SAVE_PATH)
        except Exception as e:
            log.warning("No se pudo guardar la partida: %r", e)

    # ------------------------------------------------------------
    # Hilo de red: la llamada a la IA puede tardar varios segundos:
    # se ejecuta en background y el resultado se recoge en el loop
    # principal via una Queue, para que la ventana nunca se congele.
    # ------------------------------------------------------------
    def _request_opening_line(self):
        context = ""
        if not ai_director.any_provider_available():
            context = ""
        self._start_ai_call(lambda: self.controller.start(context))

    def _start_ai_call(self, fn):
        self._ai_loading = True
        self.mode = "waiting_ai"

        def worker():
            try:
                result = fn()
            except Exception as e:
                log.exception("Error inesperado en llamada a IA: %r", e)
                result = ai_director.local_fallback_director(self.game_state, None, error=True)
            self._ai_result_queue.put(result)

        self._ai_thread = threading.Thread(target=worker, daemon=True)
        self._ai_thread.start()

    def _poll_ai_result(self):
        if not self._ai_loading:
            return
        try:
            result = self._ai_result_queue.get_nowait()
        except queue.Empty:
            return

        self._ai_loading = False
        self._apply_director_response(result)

    def _apply_director_response(self, result: ai_director.DirectorResponse):
        self.sprite.set_mode(result.expression)
        self.game_state.sakura_mode = result.expression if result.expression in (
            "normal", "happy", "blush", "sad", "angry", "surprised", "sleepy", "playful",
            "jealous", "yandere",
        ) else self.game_state.sakura_mode

        if result.background:
            self.current_background = result.background

        self.dialogue_box.set_text("Sakura", result.dialogue)
        self.reply_buttons.set_options(result.suggested_replies or [
            "Cuéntame más", "¿Qué quieres hacer?", "Nada, solo quería hablar contigo",
        ])
        self.mode = "showing_reply"
        self.showing_free_text_input = False
        audio_manager.play_sfx("notify")

        # revisa si corresponde disparar la crisis de obsesion como
        # evento especial (la propia IA ya reacciono a lo anterior;
        # esto añade un empujon narrativo extra la proxima vez que el
        # jugador hable, via contexto).
        if self.controller.check_yandere_trigger():
            audio_manager.play_sfx("glitch")

    # ------------------------------------------------------------
    def _submit_player_choice(self, text: str):
        audio_manager.play_sfx("click")
        self._start_ai_call(lambda: self.controller.submit_player_line(text))

    # ------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.QUIT:
            self.running = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F5:
                self.save_game()
                return
            if event.key == pygame.K_F11:
                self._toggle_fullscreen()
                return
            if event.key == pygame.K_ESCAPE:
                if self.mode in ("stats_overlay", "memory_overlay"):
                    self.mode = "showing_reply"
                    return
                if self.showing_free_text_input:
                    self.showing_free_text_input = False
                    return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.mode = "stats_overlay" if self.mode != "stats_overlay" else "showing_reply"
            return

        if self.mode == "stats_overlay":
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mode = "showing_reply"
            return

        if self.mode == "memory_overlay":
            self.memory_panel.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mode = "showing_reply"
            return

        if self.mode == "waiting_ai":
            return  # mientras se espera respuesta, no se puede interactuar mas

        if self.showing_free_text_input:
            self.text_input.handle_event(event)
            submitted = self.text_input.consume_submission()
            if submitted is not None:
                self._submit_player_choice(submitted)
            return

        if self.mode == "showing_reply":
            if not self.dialogue_box.is_finished():
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    self.dialogue_box.skip_to_end()
                return

            action = self.reply_buttons.handle_event(event)
            if action is not None:
                kind, value = action
                if kind == "option":
                    self._submit_player_choice(self.reply_buttons.options[value])
                elif kind == "free_text":
                    self.showing_free_text_input = True
                    self.text_input.active = True

    def _toggle_fullscreen(self):
        pygame.display.toggle_fullscreen()

    # ------------------------------------------------------------
    def update(self, dt: float):
        self.sprite.update(dt)
        if self.mode == "showing_reply":
            self.dialogue_box.update(dt)
        if self._ai_loading:
            self._loading_dots_timer += dt
        self._poll_ai_result()

    def draw(self):
        self._draw_background()

        img, pos = self.sprite.get_surface_and_pos(scale_to_height=int(self.screen_h * 0.82))
        self.screen.blit(img, pos)

        if self.mode == "waiting_ai":
            self._draw_loading_indicator()
        elif self.mode == "showing_reply":
            self.dialogue_box.draw(self.screen)
            if self.dialogue_box.is_finished() and not self.showing_free_text_input:
                self.reply_buttons.draw(self.screen)
            if self.showing_free_text_input:
                self.text_input.draw(self.screen)
            self._draw_hint("TAB: estado de la relación — F11: pantalla completa")
        elif self.mode == "stats_overlay":
            self.dialogue_box.draw(self.screen)
            rect = pygame.Rect(self.screen_w // 2 - 260, self.screen_h // 2 - 200, 520, 400)
            self.stats_panel.draw(self.screen, self.game_state, rect)
        elif self.mode == "memory_overlay":
            rect = pygame.Rect(int(self.screen_w * 0.08), int(self.screen_h * 0.08),
                                int(self.screen_w * 0.84), int(self.screen_h * 0.84))
            self.memory_panel.draw(self.screen, self.game_state, rect)

        pygame.display.flip()

    def _draw_background(self):
        filename = BACKGROUND_FILES.get(self.current_background, "bg_classroom.png")
        if image_exists(filename):
            img = load_image(filename)
            img = pygame.transform.smoothscale(img, (self.screen_w, self.screen_h))
            self.screen.blit(img, (0, 0))
        else:
            self.screen.fill((40, 20, 30))

    def _draw_hint(self, text):
        surf = self.font_small.render(text, True, (255, 255, 255))
        bg = pygame.Surface((surf.get_width() + 16, surf.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 130))
        self.screen.blit(bg, (self.screen_w - bg.get_width() - 10, 10))
        self.screen.blit(surf, (self.screen_w - surf.get_width() - 18, 14))

    def _draw_loading_indicator(self):
        dots = "." * (1 + int(self._loading_dots_timer * 2) % 3)
        text = f"Sakura está pensando{dots}"
        surf = self.font_dialogue.render(text, True, (255, 255, 255))
        rect = pygame.Rect(0, self.screen_h - int(self.screen_h * 0.12), self.screen_w, int(self.screen_h * 0.08))
        box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box.fill((20, 10, 15, 210))
        self.screen.blit(box, rect.topleft)
        self.screen.blit(surf, (rect.centerx - surf.get_width() // 2, rect.centery - surf.get_height() // 2))

    # ------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
        self.save_game()
        pygame.quit()


def main():
    fullscreen = "--windowed" not in sys.argv
    game = Game(fullscreen=fullscreen)
    game.run()


if __name__ == "__main__":
    main()
