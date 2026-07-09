"""
Modulo "Sakura nota lo que tienes abierto" — celos narrativos, de
forma segura y con limites deliberados:

  - SOLO lee nombres de procesos/programas abiertos (ej. "discord",
    "chrome"). NUNCA archivos, mensajes, fotos, historial, contenido
    de ventanas, ni nada personal.
  - Es 100% local. Nada se sube a internet excepto, opcionalmente,
    una descripcion generica de la app a la IA (ej. "una app de citas").
  - Apagado por defecto (opt-in), y requiere consentimiento explicito
    mostrado antes de activarse por primera vez.
"""
from __future__ import annotations
import subprocess
import sys
import logging

log = logging.getLogger("pc_watch")

JEALOUSY_APP_KEYWORDS = {
    "discord": "una app de chat con otras personas",
    "tinder": "una app de citas",
    "bumble": "una app de citas",
    "whatsapp": "una app de mensajes",
    "telegram": "una app de mensajes",
    "instagram": "una red social",
    "chrome": "el navegador",
    "firefox": "el navegador",
    "steam": "un juego",
    "valorant": "un juego",
    "leagueoflegends": "un juego",
}


def get_running_app_names() -> list[str]:
    """Devuelve solo NOMBRES de procesos abiertos, sin rutas, sin
    contenido, sin titulos de ventana. Best-effort multiplataforma;
    si algo falla, devuelve lista vacia sin romper el juego."""
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output(
                ["tasklist"], creationflags=0x08000000, timeout=3
            ).decode(errors="ignore")
            import re
            names = re.findall(r"^(\S+)\.exe", out, re.MULTILINE)
        elif sys.platform == "darwin":
            out = subprocess.check_output(["ps", "-axco", "command"], timeout=3).decode(errors="ignore")
            names = [l.strip() for l in out.splitlines()[1:] if l.strip()]
        else:
            out = subprocess.check_output(["ps", "-axco", "comm"], timeout=3).decode(errors="ignore")
            names = [l.strip() for l in out.splitlines()[1:] if l.strip()]

        clean = set()
        for n in names:
            n = n.lower().replace(".exe", "").strip()
            if n:
                clean.add(n)
        return sorted(clean)
    except Exception as e:
        log.warning("no se pudo listar procesos: %r", e)
        return []


def detect_jealousy_triggers(enabled: bool) -> list[tuple[str, str]]:
    if not enabled:
        return []
    apps = get_running_app_names()
    triggers = []
    for app in apps:
        for keyword, desc in JEALOUSY_APP_KEYWORDS.items():
            if keyword in app:
                triggers.append((keyword, desc))
    return triggers


def pc_watch_prompt_block(enabled: bool) -> str:
    if not enabled:
        return ""
    triggers = detect_jealousy_triggers(enabled)
    if not triggers:
        return "No notas nada sospechoso abierto en la computadora del jugador ahora mismo."
    apps_txt = ", ".join(sorted({desc for _, desc in triggers}))
    return (
        "Notas (de forma posesiva/celosa, sin explicar cómo lo sabes exactamente) "
        f"que el jugador tiene abierto ahora mismo: {apps_txt}. "
        "Puedes mencionarlo con celos si el modo lo amerita."
    )


CONSENT_TEXT = (
    "Esta función es opcional y está apagada por defecto.\n\n"
    "Si la activas, el juego revisará SOLO los NOMBRES de los programas que\n"
    "tienes abiertos en tu computadora (ej: \"discord\", \"chrome\", \"steam\"),\n"
    "para que Sakura pueda reaccionar con celos de forma narrativa.\n\n"
    "NUNCA se lee el contenido de archivos, mensajes, fotos, historial de\n"
    "navegación ni nada similar — solo nombres genéricos de apps, y todo\n"
    "se procesa localmente en tu equipo.\n\n"
    "Puedes desactivarlo en cualquier momento desde el menú de ajustes."
)
