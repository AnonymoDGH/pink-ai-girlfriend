# Pink AI Girlfriend — la IA dirige al personaje (Python puro, pantalla completa)

Visual novel tipo "novia virtual" donde **la IA controla activamente el
personaje**: decide qué dice Sakura, qué expresión pone, y si cambia de
escenario — en cada turno. No es un chat de mensajes: es una conversación
continua donde tú respondes eligiendo una de las opciones que la IA te
sugiere, o escribiendo tu propio texto libre. Corre en **pantalla completa**,
100% en Python (`pygame`), sin depender de Ren'Py.

✅ **Probado exhaustivamente**: 35 pruebas rápidas (mockeando la red) +
3 pruebas en vivo contra la API real de NVIDIA NIM, todas pasando. Se
verificó visualmente con capturas de pantalla reales de la conversación
dirigida por IA funcionando de punta a punta.

---

## 1. Instalación

Necesitas **Python 3.10+**. En Windows, descárgalo de
[python.org](https://www.python.org/downloads/) marcando "Add Python to PATH".

```bash
pip install -r requirements.txt
```

## 2. Configurar tu API key (¡ya incluida de ejemplo!)

Este proyecto usa un archivo `.env` en la raíz para las claves de API
(nunca se escriben directamente en el código). Ya viene un `.env` con
una key de **NVIDIA NIM** configurada usando el modelo `stepfun-ai/step-3.7-flash`.

```
NVIDIA_API_KEY=tu-key-aqui
NVIDIA_MODEL=stepfun-ai/step-3.7-flash
```

⚠️ **Importante sobre seguridad**: si esa key fue compartida antes en algún
chat o lugar público, **regénerala** en https://build.nvidia.com cuanto
antes y reemplázala en el `.env`. Nunca subas el archivo `.env` a repositorios
públicos (usa `.env.example` como plantilla para compartir la estructura
sin exponer la key real).

El juego también soporta **OpenRouter** (con modelos `:free`) y **OpenAI**
como respaldo, en ese orden de prioridad — si configuras varias, se intenta
la primera, y si falla, pasa a la siguiente automáticamente. Si ninguna
está disponible, Sakura sigue funcionando con un director local basado en
reglas simples (menos rico, pero nunca se rompe el juego).

## 3. Jugar

```bash
python main.py
```

El juego abre en **pantalla completa** por defecto. Para jugar en ventana:
```bash
python main.py --windowed
```

### Controles
- **Click** en una opción sugerida, o teclas **1/2/3**: elegir esa respuesta.
- **Click en "✏️ Escribir mi propia respuesta..."**: abre un campo de texto
  libre; escribe lo que quieras y presiona **Enter** para enviarlo.
- **Click / cualquier tecla** mientras el texto se está escribiendo:
  completa el texto instantáneamente (salta la animación letra por letra).
- **TAB**: abrir/cerrar el panel de estado de la relación (afecto, obsesión,
  etapa, recuerdos).
- **F11**: alternar pantalla completa / ventana.
- **F5**: guardar manualmente (también se guarda solo al cerrar el juego).
- **ESC**: cerrar paneles superpuestos (estado, texto libre).

La partida se guarda en `savegame.json` y se recarga automáticamente la
próxima vez que abras el juego — incluyendo todo el historial de
conversación con la IA, para que recuerde el contexto de sesiones pasadas.

---

## 4. Cómo funciona el "director de IA" (lo nuevo)

En vez de un chat simple pregunta-respuesta, cada turno la IA recibe:
- El estado emocional actual de Sakura (afecto, obsesión, modo).
- Los recuerdos más relevantes de la relación (ver más abajo).
- El historial reciente de la conversación.
- Lo que el jugador acaba de decir (o ningún mensaje, si la IA debe tomar
  la iniciativa).

Y responde **siempre en JSON estructurado**:

```json
{
  "dialogue": "lo que Sakura dice",
  "expression": "happy",
  "background": "cafe",
  "suggested_replies": ["opción 1", "opción 2", "opción 3"]
}
```

Esto se implementa en `engine/ai_director.py`. El juego valida y sanea la
respuesta (expresiones/fondos inválidos se ignoran de forma segura) antes
de aplicarla, así que aunque la IA "alucine" un valor raro, el juego no
se rompe.

**Nota técnica sobre el modelo**: `stepfun-ai/step-3.7-flash` es un modelo
con razonamiento interno (piensa antes de responder), por lo que el límite
de tokens está configurado alto (3000) para darle espacio a pensar y aun
así completar el JSON final — si baja demasiado, el modelo puede quedarse
"pensando" sin llegar a responder, y el sistema lo detecta y hace fallback
automáticamente.

Las llamadas a la IA corren en **un hilo aparte** (`threading`) para que
la ventana nunca se congele mientras se espera la respuesta; mientras
tanto se muestra "Sakura está pensando...".

---

## 5. Estructura del proyecto

```
pink_ai_girlfriend_py/
├── main.py                       # Ventana, pantalla completa, loop principal, UI
├── .env                          # Tus API keys (no compartir este archivo)
├── .env.example                  # Plantilla sin keys reales
├── requirements.txt
├── engine/
│   ├── ai_director.py              # La IA decide dialogo+expresion+fondo+opciones (JSON)
│   ├── conversation_controller.py  # Logica de turnos, memoria, avance de dias, cooldown yandere
│   ├── state.py                     # GameState: afecto, obsesión, recuerdos, guardado
│   ├── pc_watch.py                  # "Sakura nota lo que tienes abierto" (opt-in, seguro)
│   ├── sprite_anim.py               # Animación viva: respiración, temblor, parpadeo
│   ├── dialogue_box.py              # Caja de diálogo con efecto de texto tipo Undertale
│   ├── ui_widgets.py                 # Botones de respuesta sugerida, input de texto, paneles
│   ├── env_loader.py                  # Carga simple de .env sin dependencias extra
│   └── assets.py                       # Carga/cache de imágenes y sonidos
├── assets/
│   ├── images/                     # Sprites de Sakura (10 expresiones) y 7 fondos
│   └── audio/                      # Efectos de sonido (blip tipo Undertale y más)
└── tests/                          # Pruebas automatizadas (pytest) + pruebas en vivo
```

---

## 6. Sonido de texto tipo Undertale

En `engine/dialogue_box.py`, cada ~2 caracteres no-espacio revelados se
reproduce `assets/audio/sfx_blip.wav` — un pulso digital corto sintetizado
específicamente para esto, sin voz humana, para que combine con cualquier
personaje sin sentirse desincronizado.

---

## 7. Sistema de recuerdos (sin final)

En `engine/state.py`: cada mensaje del jugador se categoriza automáticamente
(`momento`, `confesión`, `celos`, `promesa`, `miedo`, `charla`), con recuerdos
de peso alto que casi nunca se olvidan, y probabilidad de que Sakura los
saque a relucir espontáneamente. La relación **nunca termina**: en
`conversation_controller.py`, cada `TURNS_PER_DAY` turnos de conversación
avanza un "día" narrativo, y la obsesión/afecto siguen evolucionando
indefinidamente.

---

## 8. "Sakura nota lo que tienes abierto" — celos, de forma segura

En `engine/pc_watch.py`, con límites no negociables: solo nombres de
procesos (`ps`/`tasklist` nativos), nunca contenido de archivos/mensajes,
100% local, apagado por defecto (`pc_watch_enabled = False`).

---

## 9. Correr las pruebas

```bash
pip install pytest
python -m pytest tests/ -v --deselect tests/test_ai_director_live.py
```

Para incluir las pruebas en vivo contra la API real (gasta cuota real):
```bash
python -m pytest tests/test_ai_director_live.py -v -s
```

---

## 10. Próximos pasos sugeridos

- Pantalla de consentimiento real en la UI para `pc_watch` (el módulo ya
  tiene el texto listo en `pc_watch.CONSENT_TEXT`, falta conectarlo a un
  botón en el menú).
- Más fondos/expresiones (solo agregar el `.png` y una entrada en los
  diccionarios correspondientes).
- Guardar/mostrar un indicador visual cuando cambia de fondo (transición).
- Empaquetar como `.exe` con `pyinstaller` para no requerir Python instalado.
