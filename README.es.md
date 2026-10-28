# AI Passport 随身语音 · micrófono inalámbrico y atajo de voz

Mantén pulsado el botón superior del AI Passport, habla y suelta: el texto aparece en la ventana donde estás escribiendo. Una pulsación corta del botón inferior envía Intro.

El dispositivo escucha; el ordenador reconoce. Dos formas de ejecutar el lado del ordenador:

| | Windows 10/11 x64 | Linux (Omarchy) |
| --- | --- | --- |
| Reconocimiento | tu propio método de entrada por voz (WeChat Input Method, etc.) | `voxtype` + SenseVoice, totalmente offline |
| Ruta del audio | forwarder → **VB-CABLE** → método de entrada | forwarder → ASR en proceso → escritura con `wtype` |
| Nube | depende del método de entrada | ninguna |
| Extras | — | limpieza opcional con LLM, widget de barra para Omarchy |

**Idiomas:** [English](README.md) · [中文](README.zh-CN.md) · Español · [日本語](README.ja.md)

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

Requiere un compositor wlroots: `wtype` no puede escribir en GNOME ni KDE Wayland. En Omarchy:

```bash
omarchy pkg add wtype wl-clipboard
omarchy voxtype install
voxtype setup onnx --enable
omarchy voxtype model                    # elige sensevoice-small en el diálogo
voxtype config set engine sensevoice     # obligatorio: elegir el modelo no cambia el motor
voxtype config set sensevoice.model sensevoice-small
systemctl --user restart voxtype
```

Comprueba ambos y luego instala el forwarder como servicio de usuario:

```bash
voxtype config get engine                 # debe imprimir: sensevoice
python3 linux/voice_forwarder.py --diagnose   # voxtype + wtype + UDP 33333, todo [OK]
bash linux/install.sh                     # unidad systemd de usuario, arranca al iniciar sesión
```

Detalles, opciones y solución de problemas: [linux/README.md](linux/README.md) (en chino).

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

El widget no guarda ajustes propios: toda lectura y escritura pasa por `linux/voice_tui.py`, el mismo programa que el menú de terminal, así que ambos nunca se contradicen. Sus únicas claves son `language` (`auto`, `en`, `zh`) y `repoPath`:

```bash
omarchy bar set manchunx7.ai-passport-voice language zh
omarchy-shell manchunx7.ai-passport-voice probe    # imprime el JSON de estado
```

`Target not found` significa que el QML no se cargó: mira el error QML en el log del shell, no es un problema de lógica del plugin. Notas completas: [omarchy/README.md](omarchy/README.md) (en chino).

## Limpieza con LLM (opcional, Linux)

Desactivada por defecto. Al activarla, la transcripción pasa primero por un modelo compatible con OpenAI: quita muletillas, tartamudeos y reinicios abandonados, añade puntuación y separa frases, manteniendo las palabras y el idioma. Cualquier fallo (timeout, clave incorrecta, endpoint caído) escribe el texto original: perder lo que dijiste es el único resultado inaceptable.

```bash
python3 linux/voice_tui.py          # menú: proveedor, modelo, clave, on/off, prueba
python3 linux/voice_tui.py test "呃 那个 the the 明天发货"   # solo limpieza, no escribe nada
```

Proveedores: `ollama`, `lmstudio`, `llamacpp` (locales, sin clave), `openai`, `openrouter`, `deepseek` (con clave), `custom` (cualquier base URL compatible con OpenAI). Cambiar la configuración no requiere reiniciar el servicio.

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
- [Forwarder de Linux](linux/README.md) · [Widget de Omarchy](omarchy/README.md)
- [Solución de problemas (chino)](docs/TROUBLESHOOTING.zh-CN.md)
- [Firmware y flasheo (chino)](docs/FIRMWARE.zh-CN.md)
- [Ejecutar y probar el código (chino)](docs/DEVELOPMENT.zh-CN.md)
- [Registro de validación y límites](docs/VALIDATION.md)
- [Avisos de terceros](THIRD_PARTY_NOTICES.md)

Este proyecto no ofrece cuenta de reconocimiento ni servicio ASR, y no garantiza compatibilidad con todas las versiones de los métodos de entrada. Mantén fuera de GitHub la configuración personal, las grabaciones y las cuentas del método de entrada.
