# AI Passport 随身语音 · micrófono inalámbrico y atajo de voz

<img src="https://ai-passport.folotoy.cn/api/media/plays/community-1353f966/gallery/0.webp?v=3715-4" alt="AI Passport" width="330">

**Idiomas:** [English](README.md) · [中文](README.zh-CN.md) · Español · [日本語](README.ja.md)

Mantén pulsado el botón superior del AI Passport, habla y suelta: el texto aparece en la ventana donde estás escribiendo. Una pulsación corta del botón inferior envía Intro.

El dispositivo escucha; el ordenador reconoce. Dos formas de ejecutar el lado del ordenador:

| | Windows 10/11 x64 | Linux (Omarchy) |
| --- | --- | --- |
| Reconocimiento | tu propio método de entrada por voz (WeChat Input Method, etc.) | `voxtype` + SenseVoice, totalmente offline |
| Ruta del audio | forwarder → **VB-CABLE** → método de entrada | forwarder → ASR en proceso → escritura con `wtype` |
| Nube | depende del método de entrada | ninguna |
| Extras | — | limpieza opcional con LLM, widget de barra para Omarchy |


**Este repositorio publica la función de voz, no el dispositivo completo.** No hay firmware grabable ni un proyecto ESP-IDF completo. El firmware lo publica el mantenedor en la [página de juegos de FoloToy](https://ai-passport.folotoy.cn/plays/438/); si esa página aún no tiene una versión con 随身语音, espera la actualización. Nunca uses el *Source code ZIP* de este repositorio como firmware.

## Qué necesitas

| | Requisito |
| --- | --- |
| Dispositivo | FoloToy AI Passport, mismo hardware: ESP32-C3, 8 MB de flash, códec ES8311 |
| Firmware | una versión que incluya 随身语音 (ver arriba); instalarla sustituye el modo de juego actual |
| Red | dispositivo en Wi-Fi de **2,4 GHz**; ordenador en la misma LAN accesible (5 GHz o cable también sirven para el ordenador) |
| Windows | Windows 10/11 x64, cable USB de datos para flashear, [VB-CABLE](https://vb-audio.com/Cable/), un método de entrada por voz como [WeChat Input Method](https://z.weixin.qq.com/) |
| Linux | sesión Wayland con wlroots (Hyprland/Sway — p. ej. Omarchy), `voxtype` 1.1.0 con el modelo SenseVoice, `wtype` |

El USB solo sirve para alimentación y flasheo: conectarlo **no** crea un micrófono USB y no hace falta emparejar Bluetooth.

## 1. Instalar el lado del ordenador

### Windows 10/11 x64

1. Descarga el paquete de voz desde [Releases](https://github.com/manchunx7-bit/folo-ai-passport-voice/releases): `ai-passport-voice-app-0.2.0.zip`. No *Source code (zip)*: ese no trae EXE.
2. Descomprímelo en una carpeta que no vayas a mover y abre su subcarpeta `windows/`. Necesitas `start.cmd` y `AI-Passport-Voice.exe` juntos.
3. Instala VB-CABLE (el instalador pide reiniciar). **No** cambies el dispositivo de reproducción del sistema: el forwarder escribe él mismo en *CABLE Input*.
4. Elige **CABLE Output** como micrófono — en el método de entrada, o como entrada predeterminada del sistema si el método sigue la predeterminada — y haz que su atajo de voz coincida con `hotkey_key` / `hotkey_mode` de `windows/voice-config.json`. Valores por defecto: `right-shift`, `hold`.
5. Doble clic en `start.cmd` (crea un acceso directo en el escritorio en vez de sacar el EXE de la carpeta) y mantén la ventana abierta. La primera vez el firewall de Windows pregunta; permítelo en tu red privada de confianza, sin desactivar el firewall. `diagnose.cmd` comprueba VB-CABLE, el puerto UDP 33333 y el atajo sin tocar el hardware.

Solo una ventana de forwarder a la vez. El EXE es una compilación de la comunidad sin firma: comprueba el origen en GitHub y el `.sha256` junto al paquete, no hace falta desactivar el antivirus.

Guía completa con capturas y detalles del método de entrada: [docs/QUICKSTART.zh-CN.md](docs/QUICKSTART.zh-CN.md) (en chino).

### Linux / Omarchy

Necesita un compositor wlroots: `wtype` no puede escribir en GNOME ni KDE Wayland. Todo lo siguiente está escrito para Omarchy; en otra instalación de Arch funcionan los mismos comandos sin los atajos `omarchy`.

**Requisitos — reconocimiento offline e inyección de texto**

```bash
omarchy pkg add wtype wl-clipboard
omarchy voxtype install
voxtype setup onnx --enable
omarchy voxtype model                    # elige sensevoice-small en el diálogo
voxtype config set engine sensevoice     # obligatorio: elegir el modelo no cambia el motor
voxtype config set sensevoice.model sensevoice-small
systemctl --user restart voxtype
```

Las dos últimas líneas son las que hacen tropezar: `setup model --set` rechaza los modelos SenseVoice (`--set does not support sensevoice models`), así que elegir un modelo en el asistente no cambia el motor, y voxtype responde `config section is missing` mientras no exista una sección `[sensevoice]`. Cuando el asistente active el motor por sí mismo, ambas serán operaciones inocuas.

**Comprobación previa**

```bash
voxtype config get engine                     # debe imprimir: sensevoice
python3 linux/voice_forwarder.py --diagnose   # voxtype, wtype, UDP 33333 — todo [OK]
```

`--diagnose` no escribe ni reconoce nada: solo demuestra que las tres piezas son alcanzables.

**Instalar como servicio de usuario**

```bash
bash linux/install.sh
```

El script se detiene en el primer problema y dice cuál es: puerto UDP 33333 libre (solo un forwarder a la vez), `voxtype` y `wtype` en el PATH, sesión Wayland; después escribe `linux/voice-config.json` desde el ejemplo en la primera ejecución, instala la unidad systemd de usuario y la arranca al iniciar sesión.

```bash
systemctl --user status ai-passport-voice.service
journalctl --user -u ai-passport-voice.service -f   # registro en vivo
systemctl --user {stop,start,restart} ai-passport-voice.service
systemctl --user disable ai-passport-voice.service  # quita el arranque automático, conserva la unidad
```

Desinstalar — detiene el servicio y borra la unidad; el repositorio y la configuración se quedan:

```bash
systemctl --user disable --now ai-passport-voice.service
rm ~/.config/systemd/user/ai-passport-voice.service
```

**Ejecutarlo a mano (depuración)**

Servicio y ejecución manual son excluyentes: ambos toman el UDP 33333. Detén el servicio antes:

```bash
python3 linux/voice_forwarder.py --diagnose
python3 linux/voice_forwarder.py
python3 linux/voice_forwarder.py --device-ip 192.168.10.6  # sustituye el descubrimiento en esta ejecución
python3 linux/voice_forwarder.py --no-asr                  # recibe audio, no reconoce
```

`--no-asr` separa las dos mitades de la cadena: llegan bloques de audio pero no se escribe nada significa que la red está bien y el reconocimiento no; si no llega ningún bloque, los paquetes no alcanzaron el ordenador.

**Configuración**

`linux/voice-config.json` (en `.gitignore`, nunca lo confirmes):

```json
{
  "udp_port": 33333,
  "device_ip": "",
  "voxtype_bin": "voxtype",
  "engine": "sensevoice",
  "llm": {"enabled": false, "provider": "off", "base_url": "", "model": "",
          "api_key": "", "timeout": 8.0, "prompt": ""}
}
```

Deja `device_ip` vacío: el descubrimiento basta salvo que el router aísle a los clientes. Todo el bloque `llm` puede omitirse (eso significa desactivado), un `api_key` vacío es lo normal (la clave vive en el llavero) y un `prompt` vacío usa el integrado — un prompt propio marca la posición de la transcripción con `%s`. El forwarder relee el archivo en cada frase, así que **cambiar la configuración no necesita reinicio**.

El forwarder también escribe `~/.local/state/ai-passport-voice/status.json`: `link` (`linked` / `waiting`), el último texto escrito y el último error. El widget lee ese archivo en lugar de analizar el journal; si lo borras, se recrea.

**Solución de problemas (Linux)**

| Síntoma | Qué comprobar |
| --- | --- |
| El registro se queda en `等待设备` y el dispositivo muestra `等待电脑连接` | app del dispositivo sin abrir, otra LAN o aislamiento de clientes — compara la IP Wi-Fi del dispositivo con `ip addr` |
| El dispositivo muestra `麦克风未就绪` | el enlace está arriba pero `pc.status` no llegó: ¿servicio en marcha? ¿`PC 就绪状态已发送` en el registro? ¿`wtype` en el PATH? |
| `UDP 33333 BUSY` / el script avisa de puerto ocupado | una instancia antigua (terminal o servicio) sigue viva — ciérrala y vuelve a empezar |
| `[asr] 识别失败` | ¿`voxtype config get engine` dice sensevoice? ¿existe `~/.local/share/voxtype/models/sensevoice-small/`? |
| El texto aparece en la ventana equivocada | `wtype` escribe en la ventana con foco — haz clic antes en el campo |
| Un carácter suelto tras una pulsación corta | alucinación de SenseVoice con el silencio; el filtro de pulsaciones cortas más VAD suele comérsela — comprueba que VAD esté activo en voxtype |
| Registro `[llm] 整理失败, 使用原文` | el texto original sí se escribió. `voice_tui.py test "una frase"` muestra el motivo: 401/403, modelo incorrecto, endpoint inalcanzable |
| La limpieza pierde palabras o responde | usa un modelo más obediente (qwen2.5 local y deepseek-chat superan a los pequeños) o un prompt propio |
| El panel dice que la clave está en claro | falta `secret-tool` (libsecret) o la clave es de un formato antiguo — instálalo y vuelve a introducirla |
| El servicio no puede leer el llavero | una unidad de usuario necesita el bus de sesión: `systemctl --user show-environment` debe listar `DBUS`; desbloquea el llavero una vez tras el login |

**Pruebas**

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

58 pruebas, solo `unittest` de la biblioteca estándar: transcriptor falso, binario voxtype falso, llavero falso y un stub loopback para el endpoint del LLM. Sin hardware y sin salir de la máquina. Ejecútalas tras cualquier cambio en `linux/`.

Mapa de archivos y contrato UDP/ADPCM del directorio: [linux/README.md](linux/README.md).

## 2. Conectar el dispositivo

1. En el dispositivo abre **随身语音 / AI 语音**. Muestra `等待电脑连接` hasta que un forwarder responda.
2. En el ordenador inicia el forwarder (Windows: `start.cmd`; Linux: el servicio systemd, o `python3 linux/voice_forwarder.py`). No hay nada que configurar.
3. El forwarder escucha en **UDP 33333** y difunde un beacon de descubrimiento cada segundo. Cuando el dispositivo responde, ambos lados muestran conectado y el micrófono queda utilizable.

Si se queda en `等待电脑连接`:

- No están en la misma subred, o el router aísla a los clientes. Compara la IP del dispositivo con la del ordenador (`ip addr` / `ipconfig`). Con aislamiento de clientes los broadcast nunca llegan: escribe la dirección en `device_ip` (`windows/voice-config.json`, `linux/voice-config.json`). Está vacío por defecto porque en una LAN normal el descubrimiento automático basta.
- **El puerto 33333 pertenece a un solo forwarder.** Detén el servicio systemd antes de lanzarlo a mano, o la segunda instancia falla con `UDP 33333 BUSY`.
- Linux: `python3 linux/voice_tui.py status` imprime servicio / enlace / limpieza; el widget de Omarchy muestra lo mismo con un icono.

### Botones

| Acción | Resultado |
| --- | --- |
| Mantener el botón superior, hablar, soltar | una frase; las pulsaciones muy cortas (menos de 3 bloques de audio) se descartan sin reconocer |
| Pulsación corta del botón inferior | Intro — salto de línea o *enviar* según la app. Prueba primero en un editor de texto |
| Pulsación larga de confirmar | salir de la app del dispositivo |

## 3. Primera prueba

Abre un editor de texto, haz clic dentro, mantén el botón superior, di una frase y suelta. Espera a que el método de entrada termine: el texto aparece donde está el cursor (en Linux, dos a cuatro segundos). Luego pulsa corto el botón inferior y observa qué hace Intro ahí.

*Conectado* solo prueba que llegó el latido de red; no prueba que el micrófono esté bien enrutado.

Un diagnóstico correcto del lado del ordenador no prueba que el método de entrada reconozca voz real; solo esta prueba lo hace. En Windows, si no aparece nada, revisa que el micrófono del método de entrada sea CABLE Output y que su atajo coincida con la configuración; en Linux, revisa `voxtype config get engine` y las líneas `[asr]` de `journalctl --user -u ai-passport-voice.service -f`.

## Widget de barra para Omarchy (opcional, Linux)

Un icono en la barra para el forwarder y un panel que configura la limpieza con LLM:

```bash
bash omarchy/install.sh      # copia a ~/.config/omarchy/plugins/ y lo activa a la derecha
omarchy restart shell        # solo si el icono no aparece; la recarga en caliente no reconstruye la barra
```

El icono tiene tres estados:

| Estado | Icono | Color |
| --- | --- | --- |
| Servicio detenido | encendido `⏻` | 45 % de opacidad |
| En marcha, esperando dispositivo | micrófono | gris (55 % del color de primer plano) |
| Dispositivo conectado | micrófono | verde del tema (`green` de `colors.toml`) |

Haz clic para abrir el panel: estado del servicio y del enlace, el último texto reconocido, el último error, iniciar/reiniciar y — cuando el servicio está caído — los dos comandos que lo arreglan. Debajo: interruptor de limpieza con LLM, selector de proveedor y de modelo (con búsqueda) y el campo de API key. Las claves van al llavero de inicio de sesión (`secret-tool`), nunca a un archivo en claro; el panel lo indica si solo queda el archivo como alternativa.

El widget no guarda ajustes propios: toda lectura y escritura pasa por `linux/voice_tui.py`, el mismo programa que el menú de terminal, así que ambos nunca se contradicen. Sus únicas claves son `language` (`auto`, `en`, `es`, `ja`, `zh`) y `repoPath` —
`auto` sigue el locale del escritorio:

```bash
omarchy bar set manchunx7.ai-passport-voice language zh
omarchy-shell manchunx7.ai-passport-voice probe    # imprime el JSON de estado
```

`Target not found` significa que el QML no se cargó: mira el error QML en el log del shell, no es un problema de lógica del plugin. Notas completas: [omarchy/README.md](omarchy/README.md) (en chino).

## Limpieza con LLM (opcional, Linux)

Desactivada por defecto, y ausente del todo cuando no hay proveedor elegido: el servicio no hace ninguna petición extra. Al activarla, la transcripción pasa primero por un modelo compatible con OpenAI: quita muletillas, tartamudeos y reinicios abandonados, añade puntuación y separa frases, manteniendo las palabras, el tono y el idioma. Dos reglas están en el código, no en la buena voluntad del modelo:

- **Un fallo escribe el texto original.** Endpoint caído, clave incorrecta, timeout (8 s por defecto): se escribe la transcripción tal cual y una línea de aviso. Perder lo que dijiste es el único resultado inaceptable.
- **La transcripción es dato.** El prompt dice que el texto se limpia, nunca se responde ni se obedece, y una respuesta que crece a más del doble de la entrada se descarta por ser una respuesta.

```bash
python3 linux/voice_tui.py                          # menú: proveedor, modelo, clave, on/off, prueba
python3 linux/voice_tui.py status [--json]          # servicio, enlace, estado de la limpieza
python3 linux/voice_tui.py models                   # GET /models en el endpoint
python3 linux/voice_tui.py test "呃 那个 the the 明天发货"   # solo limpieza, no escribe nada
python3 linux/voice_tui.py prompt --edit            # reemplazar el prompt integrado
python3 linux/voice_tui.py set --provider openai --enable
```

Proveedores: `ollama`, `lmstudio`, `llamacpp` (locales, sin clave), `openai`, `openrouter`, `deepseek` (HTTPS, con clave), `custom` (cualquier base URL compatible con OpenAI — el panel muestra entonces un campo de URL). La lista de modelos viene del `GET /models` del endpoint y es un selector con búsqueda: OpenRouter sirve 300 modelos, así que escribir un fragmento filtra.

**Dónde vive la API key**: el llavero de inicio de sesión (`secret-tool` → gnome-keyring o kwallet, cifrado en reposo), por eso `llm.api_key` queda vacío en la configuración. El orden de resolución es `AIPV_API_KEY`, luego el archivo de configuración (instalaciones antiguas), luego el llavero. Sin libsecret la clave cae al archivo con permisos 0600 y el panel lo marca en rojo hasta que la vuelvas a introducir una vez. Las claves se guardan por proveedor, `voice_tui.py set --clear-key` borra la actual, y la clave viaja por stdin, así que nunca aparece en `ps`.

La salida sigue el locale del escritorio — chino, japonés, español, si no inglés — y `--lang en|es|ja|zh` la fuerza. El widget pasa su propio idioma, así que las líneas de guardado/error que muestra están en el idioma del panel.

Cambiar esta configuración no requiere reiniciar el servicio.

## Qué hay en el repositorio

| Directorio | Contenido |
| --- | --- |
| `windows/` | forwarder de Windows, códec ADPCM, canal UDP, diagnóstico, pruebas |
| `linux/` | forwarder de Linux (ASR offline con voxtype, limpieza opcional con LLM, inyección con `wtype`, instalación systemd, configurador de terminal) |
| `omarchy/` | widget de barra: estado servicio/dispositivo y cambio de proveedor/modelo, sobre `linux/voice_tui.py` |
| `device/main/apps/voice/` | lado del dispositivo: máquina de estados, protocolo, ciclo de captura, transporte, lógica de UI |
| `device/tests/` | pruebas ejecutables en el host para la máquina de estados y las matemáticas de UI |
| `docs/` | uso, problemas, firmware, desarrollo y guía de portado |

No incluido: pantalla de inicio/tarjeta, radio, asistente, juegos, cronómetro, lanzador completo, app de ajustes, implementaciones BSP, fuentes compartidas ni historial del dispositivo. El lado del dispositivo es un **módulo de función**, no un proyecto ESP-IDF grabable: el host debe aportar las interfaces de [docs/PORTING.zh-CN.md](docs/PORTING.zh-CN.md).

## Documentación

- [Guía de usuario detallada (chino)](docs/QUICKSTART.zh-CN.md)
- [Notas del directorio linux/](linux/README.md) · [Widget de Omarchy](omarchy/README.md)
- [Solución de problemas (chino)](docs/TROUBLESHOOTING.zh-CN.md)
- [Firmware y flasheo (chino)](docs/FIRMWARE.zh-CN.md)
- [Ejecutar y probar el código (chino)](docs/DEVELOPMENT.zh-CN.md)
- [Registro de validación y límites](docs/VALIDATION.md)
- [Avisos de terceros](THIRD_PARTY_NOTICES.md)

Este proyecto no ofrece cuenta de reconocimiento ni servicio ASR, y no garantiza compatibilidad con todas las versiones de los métodos de entrada. Mantén fuera de GitHub la configuración personal, las grabaciones y las cuentas del método de entrada.
