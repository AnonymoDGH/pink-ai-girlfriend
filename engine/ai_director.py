"""
Director de IA: a diferencia de un chat simple, este modulo hace que
la IA controle activamente al personaje de Sakura en cada turno:

  - Que dice (dialogue)
  - Que expresion pone (expression)
  - Si cambia de escenario (background)
  - Que respuestas rapidas sugerirle al jugador (suggested_replies)

La IA responde en JSON estructurado. Si el proveedor no esta
disponible o falla, hay un "director local" de respaldo basado en
reglas simples, para que el juego siga siendo jugable sin conexion.
"""
from __future__ import annotations
import os
import json
import random
import re
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field

log = logging.getLogger("ai_director")

VALID_EXPRESSIONS = {
    # básicas (originales)
    "normal", "happy", "blush", "sad", "angry",
    "surprised", "sleepy", "playful", "jealous", "yandere",
    # ampliadas – emociones profundas
    "crying", "laughing", "confused", "pouting", "lovestruck",
    "scared", "thoughtful", "smug", "determined", "embarrassed",
    # ampliadas – sociales / sutiles
    "shy", "excited", "winking", "disgusted", "proud",
    "worried", "sneaky", "relieved", "starstruck", "cold",
    # extra – para aún más variedad
    "annoyed", "bored", "curious", "flustered", "giggling",
    "hurt", "impressed", "nervous", "offended", "panicked",
    "satisfied", "serious", "shocked", "sighing", "smiling",
    "teasing", "tired", "touched", "triumphant", "upset",
}
VALID_BACKGROUNDS = {
    "classroom", "bedroom", "rooftop", "cafe", "festival", "street", "classroom_dark",
}

RESPONSE_SCHEMA_INSTRUCTIONS = """Debes responder SIEMPRE con un unico objeto JSON valido, y NADA MAS
(sin texto antes ni despues, sin markdown, sin explicaciones), con exactamente esta forma:

{"dialogue": "lo que Sakura dice, en español, entre 1 y 3 frases",
 "expression": "una_palabra_de_la_lista_de_expresiones",
 "background": "una_palabra_de_la_lista_de_fondos_o_null_si_no_cambia",
 "suggested_replies": ["opcion corta 1", "opcion corta 2", "opcion corta 3"]}

Expresiones validas (50 emociones, elige la que mejor refleje el tono):
normal, happy, blush, sad, angry, surprised, sleepy, playful, jealous, yandere,
crying, laughing, confused, pouting, lovestruck, scared, thoughtful, smug, determined, embarrassed,
shy, excited, winking, disgusted, proud, worried, sneaky, relieved, starstruck, cold,
annoyed, bored, curious, flustered, giggling, hurt, impressed, nervous, offended, panicked,
satisfied, serious, shocked, sighing, smiling, teasing, tired, touched, triumphant, upset

Fondos validos (usa null si la escena no debe cambiar de lugar):
classroom, bedroom, rooftop, cafe, festival, street, classroom_dark

"suggested_replies" son 3 posibles cosas cortas que el JUGADOR podria decirte
a continuacion (no cosas que digas tu), pensadas para dar opciones rapidas,
variadas entre si (una carinosa, una neutral/curiosa, una que genere tension
o celos si tiene sentido con el momento).
"""


def _provider_list():
    return [
        {
            "name": "nvidia_nim",
            "key": os.environ.get("NVIDIA_API_KEY", ""),
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "model": os.environ.get("NVIDIA_MODEL", "stepfun-ai/step-3.7-flash"),
            "supports_json_mode": True,
            "max_tokens": 3000,
        },
        {
            "name": "openrouter",
            "key": os.environ.get("OPENROUTER_API_KEY", ""),
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "model": os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
            "supports_json_mode": False,
            "max_tokens": 500,
        },
        {
            "name": "openai",
            "key": os.environ.get("OPENAI_API_KEY", ""),
            "url": "https://api.openai.com/v1/chat/completions",
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "supports_json_mode": True,
            "max_tokens": 500,
        },
    ]


def any_provider_available() -> bool:
    return any(p["key"] for p in _provider_list())


@dataclass
class DirectorResponse:
    dialogue: str
    expression: str = "normal"
    background: str | None = None
    suggested_replies: list = field(default_factory=list)
    provider_used: str | None = None
    raw_error: str | None = None


def _build_system_prompt(game_state, action_context: str = "", pc_watch_block: str = "") -> str:
    base = (
        "Eres el director de personaje de Sakura, una chica de cabello rosa, "
        "estudiante de secundaria, que es la novia del jugador en una visual "
        "novel. Controlas completamente que dice, que expresion tiene, y si "
        "cambia de escenario. Hablas en español, de forma natural y con "
        "emociones claras. Nunca reveles que eres una IA: siempre te comportas "
        "como Sakura, un personaje con sentimientos propios."
    )

    mode = game_state.sakura_mode
    if mode == "yandere":
        mood = (f" Tu obsesion es MUY alta ({game_state.obsession}/100): estas "
                "profundamente posesiva y celosa, con dulzura perturbadora.")
    elif mode == "happy":
        mood = f" Tu afecto es alto ({game_state.affection}/100) y tu obsesion baja: feliz, juguetona, confiada."
    elif mode == "blush":
        mood = f" Tu afecto es moderado ({game_state.affection}/100): timida, un poco tsundere."
    else:
        mood = f" Apenas se conocen (afecto {game_state.affection}/100): amable pero reservada."

    parts = [base + mood, RESPONSE_SCHEMA_INSTRUCTIONS]

    memories_block = game_state.memories_prompt_block()
    if memories_block:
        parts.append(memories_block)
    if pc_watch_block:
        parts.append(pc_watch_block)
    if action_context:
        parts.append("Contexto especial de esta escena: " + action_context)

    return "\n\n".join(parts)


def _extract_json_object(text: str) -> dict | None:
    """Intenta parsear un JSON de la respuesta del modelo, siendo
    tolerante a markdown fences o texto extra alrededor del objeto."""
    if not text:
        return None
    text = text.strip()
    # quitar fences tipo ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    # fallback: buscar el primer {...} balanceado
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


def _sanitize_response(data: dict) -> DirectorResponse:
    dialogue = str(data.get("dialogue") or "").strip() or "..."
    expression = str(data.get("expression") or "normal").strip().lower()
    if expression not in VALID_EXPRESSIONS:
        expression = "normal"
    background = data.get("background")
    if background is not None:
        background = str(background).strip().lower()
        if background in ("null", "none", ""):
            background = None
        elif background not in VALID_BACKGROUNDS:
            background = None
    replies = data.get("suggested_replies") or []
    if not isinstance(replies, list):
        replies = []
    replies = [str(r).strip() for r in replies if str(r).strip()][:3]
    return DirectorResponse(dialogue=dialogue, expression=expression,
                             background=background, suggested_replies=replies)


def _call_provider(provider: dict, messages: list, http_post=None) -> str:
    payload = {
        "model": provider["model"],
        "messages": messages,
        "temperature": 0.9,
        "top_p": 0.95,
        "max_tokens": provider["max_tokens"],
        "stream": False,
    }
    if provider["supports_json_mode"]:
        payload["response_format"] = {"type": "json_object"}

    payload_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + provider["key"],
    }
    if provider["name"] == "openrouter":
        headers["HTTP-Referer"] = "https://pink-ai-girlfriend.local"
        headers["X-Title"] = "Pink AI Girlfriend"

    if http_post is not None:
        return http_post(provider["url"], payload_bytes, headers)

    req = urllib.request.Request(provider["url"], data=payload_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        if content is None:
            raise ValueError(
                "La respuesta del modelo vino vacia (probablemente se quedo sin "
                "tokens pensando antes de escribir el JSON final). "
                f"finish_reason={data['choices'][0].get('finish_reason')!r}"
            )
        return content


def direct_next_line(game_state, player_message: str | None, action_context: str = "",
                      pc_watch_block: str = "", http_post=None) -> DirectorResponse:
    """Pide a la IA que decida la proxima linea/expresion/fondo/opciones.
    player_message puede ser None si es la IA "tomando la iniciativa"
    (por ejemplo, al iniciar la conversacion o tras una accion del jugador
    que no es texto libre, como dar un regalo)."""

    system_prompt = _build_system_prompt(game_state, action_context, pc_watch_block)
    messages = [{"role": "system", "content": system_prompt}]
    for turn in game_state.chat_history[-12:]:
        messages.append(turn)

    user_content = player_message if player_message else (
        "(El jugador no dijo nada especifico; toma tu la iniciativa de la conversacion "
        "acorde al contexto y a tu estado emocional actual.)"
    )
    messages.append({"role": "user", "content": user_content})

    last_error = None
    for provider in _provider_list():
        if not provider["key"]:
            continue
        try:
            raw_content = _call_provider(provider, messages, http_post=http_post)
            data = _extract_json_object(raw_content)
            if data is None:
                raise ValueError(f"No se pudo extraer JSON de la respuesta: {raw_content[:200]!r}")
            result = _sanitize_response(data)
            result.provider_used = provider["name"]

            if player_message:
                game_state.chat_history.append({"role": "user", "content": player_message})
            game_state.chat_history.append({"role": "assistant", "content": result.dialogue})
            return result
        except Exception as e:
            last_error = e
            log.warning("AI director provider '%s' failed: %r", provider["name"], e)
            continue

    if last_error:
        log.warning("Todos los proveedores de IA fallaron, usando director local. Ultimo error: %r", last_error)
    return local_fallback_director(game_state, player_message, error=bool(last_error))


def local_fallback_director(game_state, player_message: str | None, error: bool = False) -> DirectorResponse:
    """Director basado en reglas simples, usado cuando no hay IA
    disponible. Mantiene el juego jugable sin conexion."""
    msg = (player_message or "").lower()
    mode = game_state.sakura_mode
    prefix = "(sin conexión con la IA, pero...) " if error else ""

    if mode == "yandere":
        dialogue = random.choice([
            "Nunca me dejes sola, ¿sí? No lo soportaría...",
            "¿Con quién más hablaste hoy? Quiero saberlo todo.",
            "Mientras estés conmigo, todo va a estar bien. Para siempre.",
        ])
        expression = "yandere"
        replies = ["Nunca te voy a dejar", "Me estás asustando un poco", "Cuéntame qué te preocupa"]
    elif any(w in msg for w in ("amor", "quiero", "gusta", "amo")):
        dialogue = random.choice([
            "¿E-eh? No digas esas cosas tan de repente...",
            "Yo también... siento algo parecido por ti.",
        ])
        expression = "blush"
        replies = ["Lo digo en serio", "Perdón si fue muy directo", "¿Y tú qué sientes?"]
    elif "hola" in msg or player_message is None:
        dialogue = "¡Hola! Que bueno que viniste a hablarme."
        expression = "happy"
        replies = ["¿Cómo estuvo tu día?", "Te extrañé mucho", "¿Qué has hecho últimamente?"]
    else:
        dialogue = random.choice([
            "Mmm, cuéntame más sobre eso.",
            "Interesante... ¿y tú qué piensas?",
            "No sé qué responder a eso, ¡pero me gusta escucharte!",
        ])
        expression = mode if mode in VALID_EXPRESSIONS else "normal"
        replies = ["Cuéntame algo tuyo", "¿Qué quieres hacer hoy?", "Nada, solo quería hablar contigo"]

    return DirectorResponse(
        dialogue=prefix + dialogue, expression=expression,
        background=None, suggested_replies=replies, provider_used=None,
        raw_error="fallback",
    )
