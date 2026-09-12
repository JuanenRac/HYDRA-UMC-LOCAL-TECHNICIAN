<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="Banner de HYDRA-UMC-LOCAL-TECHNICIAN" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🛡️ Técnico de IA Local con Permisos Acotados por Política

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Lenguaje-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Núcleo-solo%20stdlib-brightgreen.svg" alt="Núcleo solo stdlib">
  <img src="https://img.shields.io/badge/Fase-3%20de%206-367BF5.svg" alt="Fase 3 de 6">
</p>

> **Estado: v0.0.4, funcional - Fase 3 de 6, parcial (orquestador de
> herramientas).** La Fase 0 definió la política real de niveles de
> riesgo (`policy/risk_levels.py`), una lista blanca fija de
> herramientas (`policy/tool_matrix.py`), los cinco contratos mínimos
> reales que toda futura llamada a herramienta deberá validar
> (`contracts/*.schema.json` + `contracts.py`), un saneamiento real de
> secretos portado del ya probado `log_redaction.py` de
> HYDRA-UMC-OPS-AGENT, y el criterio de salida literal de la propia Fase
> 0: una prueba adversarial real que demuestra que un documento
> malicioso recuperado nunca puede disparar una llamada a herramienta ni
> filtrar un secreto. La Fase 3 conecta 7 de las 9 herramientas OBSERVE
> declaradas a un manejador real (`orchestrator/dispatch.py`):
> `service.status`, `storage.usage`, `network.port_status`,
> `network.connectivity`, `system.temperature`, `manifest.read` y `logs.read` - cada
> una resolviendo solo un nombre simbólico en lista blanca
> (`orchestrator/allowlist.py`), nunca una ruta/host/puerto/URL en bruto
> que un documento recuperado pudiera aportar. Todavía no existe motor de
> inferencia, índice RAG, ni
> integración con HYDRA-UMC-SERVER - ver
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para la superficie de
> comandos exacta que existe hoy.

---

**Comprobación de honestidad - qué funciona realmente hoy:** la política de niveles de riesgo (`policy/risk_levels.py`), la lista fija de herramientas permitidas (`policy/tool_matrix.py`), los cinco validadores de contrato (`contracts.py` + `contracts/*.schema.json`), el límite de defensa contra inyecciones (`knowledge/trust.py`, `knowledge/redaction.py`), y ahora 7 manejadores reales de herramientas OBSERVE (`orchestrator/dispatch.py` + `orchestrator/allowlist.py`: `service.status`, `storage.usage`, `network.port_status`, `network.connectivity`, `system.temperature`, `manifest.read`, `logs.read`) son todos reales y están testeados (103 tests más 28 subtests pasando entre `tests/unit/` y `tests/adversarial/`). Las otras 2 herramientas en `TOOL_MATRIX` (`process.list`, `update.pending`) siguen siendo `implemented=False` a propósito - cada una necesita su propio diseño separado (filtrado, o una integración real con HYDRA-UMC-UPDATER), no es un descuido. Todavía no hay motor de inferencia, ni índice RAG, ni integración con HYDRA-UMC-SERVER en ningún lugar de este repositorio - las Fases 1, 2, 4 y 5 del Roadmap más abajo siguen siendo totalmente aspiracionales, sin ningún código detrás, y la propia Fase 3 es parcial (7 de 9 herramientas). Ver `CHANGELOG.md` para lo que se ha entregado exactamente hasta ahora.

---

## 1. 🛠️ VISIÓN TÉCNICA

HYDRA-UMC-LOCAL-TECHNICIAN es una IA local especializada para el propio
ecosistema HYDRA-UMC: observa, explica, diagnostica y propone
mantenimiento para los servicios y nodos del propio ecosistema - nunca
entrena un nuevo modelo fundacional, y nunca actúa generando texto. Su
plataforma objetivo es la CM5, usando el acelerador Hailo-10H una vez
instalado, pero la Fase 0 no necesita ninguno de los dos: todo en esta
entrega es Python puro validando datos puros.

**Principio no negociable:** la IA nunca obtiene autoridad generando una
respuesta. La política, los permisos y la confirmación humana deciden
cada acción real - nunca las propias palabras del modelo.

Esta entrega (Fase 0) trae cuatro piezas reales y de utilidad
independiente:

1. **Política de niveles de riesgo** (`policy/risk_levels.py`) - seis
   niveles ordenados, de `INFORM` a `PHYSICAL_ACTION`, cada uno con una
   política real y probada (si puede leer una herramienta, si puede
   mutar, si requiere confirmación, si está implementado). Los dos
   niveles superiores están declarados solo por completitud del
   contrato - genuinamente no implementados en ningún lugar de este
   código.
2. **Matriz de herramientas** (`policy/tool_matrix.py`) - una lista
   blanca fija de nueve nombres reales de herramienta de nivel
   `OBSERVE`. Un nombre de herramienta ausente de este diccionario nunca
   puede llamarse, punto - 7 de las 9 ya están conectadas a un manejador
   real (ver el punto 5 más abajo), las otras 2 siguen con
   `implemented=False` a propósito.
3. **Contratos reales** (`contracts/*.schema.json` + `contracts.py`) -
   `ToolRequest`, `ToolResult`, `MaintenanceProposal`, `EvidenceBundle` y
   `PatchVerificationReport`, cada uno con un archivo JSON Schema
   normativo y un validador Python solo-stdlib copiado de él campo a
   campo.
4. **Límite de defensa contra inyección** (`knowledge/trust.py` +
   `knowledge/redaction.py`) - el contenido no confiable (un README, una
   línea de log, un mensaje de commit) siempre se envuelve como
   `UntrustedText`, un tipo sin ningún método que pueda producir jamás
   una llamada a herramienta. La única forma real de construir un
   `ToolRequest` toma campos ya tipados y ya separados, y rechaza
   cualquier nombre de herramienta no registrado o no implementado antes
   de que el objeto llegue a existir.

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

No hay invocación por defecto/sin argumentos ni interfaz gráfica en esta
entrega - ver [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para la
superficie de comandos real y completa.

## 2. 🧱 ARQUITECTURA Y DECISIONES DE DISEÑO

- **La IA nunca obtiene autoridad generando una respuesta.** Cada
  decisión de diseño de esta entrega existe para proteger este único
  principio - ver [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) para
  el modelo completo.
- **Una herramienta debe estar registrada antes de poder llamarse
  jamás.** `TOOL_MATRIX` de `policy/tool_matrix.py` es la lista completa
  y fija; que `lookup_tool()` devuelva `None` es un rechazo
  incondicional, nunca un caso donde adivinar un nivel de riesgo por
  defecto.
- **El contenido no confiable nunca puede convertirse en un comando.**
  La defensa es arquitectónica (un tipo sin ningún método que produzca
  una herramienta), no un filtro que intenta reconocer texto "con forma
  de instrucción" - un juego perdido de antemano contra una inyección de
  prompt decidida. Ver `tests/adversarial/test_injection_defense.py`, el
  criterio de salida literal de la propia Fase 0.
- **La fuente normativa de un contrato es su archivo JSON Schema.** Las
  listas de campos y validadores de `contracts.py` se copian de
  `contracts/*.schema.json`, campo a campo, siguiendo la misma
  convención que `validation.py` de HYDRA-UMC-SDK - no una segunda
  fuente de verdad independiente.
- **El saneamiento de secretos reutiliza código ya probado.**
  `knowledge/redaction.py` es un port byte a byte (solo cambia el
  comentario de cabecera) del ya probado `log_redaction.py` de
  HYDRA-UMC-OPS-AGENT - el problema de fondo (reconocer formas reales y
  bien conocidas de secreto sin una heurística difusa) es idéntico aquí.
- **`PRIVILEGED_CHANGE` y `PHYSICAL_ACTION` siguen sin implementarse.**
  Una puerta deliberada y permanente hasta que exista un diseño
  dedicado, un camino de autorización separado y, para la acción física,
  interlocks reales - no un olvido por completar más adelante.
- **Esta entrega solo declara y valida - todavía no actúa.** No existe
  motor de inferencia, índice RAG, ejecución real de herramientas, ni
  integración con HYDRA-UMC-SERVER en ningún lugar de este repositorio
  todavía.

## 📂 ESTRUCTURA DE DIRECTORIOS

```
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/
│   ├── policy/
│   │   ├── risk_levels.py    # RiskLevel + RiskLevelPolicy: los seis niveles, política real por nivel
│   │   └── tool_matrix.py    # TOOL_MATRIX: la lista blanca fija y real de herramientas (9 nombres OBSERVE)
│   ├── knowledge/
│   │   ├── redaction.py      # Saneamiento real de secretos, portado de HYDRA-UMC-OPS-AGENT
│   │   └── trust.py          # UntrustedText + build_tool_request_from_model_output(): el límite de defensa contra inyección
│   ├── contracts.py           # Validador real solo-stdlib para los cinco contratos mínimos
│   └── cli.py                 # Subcomando contracts validate + --version
├── contracts/                  # Archivos JSON Schema normativos (draft 2020-12) para los cinco contratos
├── tests/
│   ├── unit/                   # Pruebas reales de cada módulo anterior
│   ├── adversarial/            # test_injection_defense.py - el criterio de salida literal de la propia Fase 0
│   └── fixtures/                # Fixtures JSON válidos/inválidos para cada contrato
├── docs/
│   ├── ARCHITECTURE.md         # Propósito, las cinco piezas objetivo, arquitectura objetivo, relaciones del ecosistema
│   ├── SECURITY_MODEL.md       # Los seis niveles de riesgo, reglas de datos/secretos, defensa contra inyección
│   ├── CLI_REFERENCE.md        # contracts validate, flags, códigos de salida
│   └── CONTRACTS.md            # La forma real campo a campo de los cinco contratos
├── images/                      # Medios e iconos de la app
├── build.sh / build.bat        # venv + instalación editable + comprobación + pruebas
├── build-test.sh / .bat        # Solo validación de build no mutante
├── run.sh / run.bat            # Reenvía un comando CLI real
├── bump_version.py             # Incremento "odómetro" de todo el ecosistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py    # Sincroniza la versión de hydra-umc.project.json con la nativa (--sync)
```

## ⚙️ GUÍA DE COMPILACIÓN Y EJECUCIÓN

```bash
chmod +x build.sh   # una sola vez
./build.sh          # crea .venv, pip install -e ".[dev]", comprobación + pruebas
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

En Windows: `build.bat`, luego `run.bat contracts validate ...` /
`run.bat --version`. `build-test.sh`/`.bat` hace la misma comprobación de
sintaxis Python no mutante que ya hace el propio workflow de CI, sin
tocar la versión del proyecto ni el CHANGELOG - NO ejecuta la suite de
pruebas; ejecuta `./build.sh`/`build.bat` (o `pytest tests/`
directamente) para la suite de pruebas local completa.

**Resolución de problemas**

- `contracts validate` sale con código `1` y `INVALID: ...`: lee el
  mensaje - nombra el campo exacto y el motivo, no solo que algo falló.
  Revisa [docs/CONTRACTS.md](docs/CONTRACTS.md) para la forma real
  esperada de cada uno de los cinco contratos.
- Una prueba en `tests/adversarial/` falla: es el criterio de salida
  literal de la propia Fase 0 - trata cualquier fallo ahí como una
  regresión real del límite de defensa contra inyección, nunca como una
  prueba a relajar.

## 🚀 HOJA DE RUTA

Esta versión trae la Fase 0 y parte de la Fase 3. Lo que queda, en orden de fases:

- **Fase 1 - Conocimiento recuperable.** Un índice local y versionado de
  documentación, manifiestos, contratos y runbooks aprobados - nunca
  entrenado a ciegas sobre todo el disco.
- **Fase 2 - Motor de inferencia local.** Un LLM pequeño compatible con
  Hailo-10H (candidatos: Qwen2.5-1.5B-Instruct, Qwen2.5-Coder-1.5B,
  Qwen3-1.7B-Instruct), elegido solo una vez verificadas la
  compatibilidad Hailo real, la latencia, la calidad de idioma, el
  consumo y la licencia.
- **Fase 3 - Orquestador de herramientas (parcial: 7 de 9).** Código
  determinista que conecta los primeros manejadores reales de
  herramienta de nivel `OBSERVE` a `TOOL_MATRIX`, con la política
  forzada en cada llamada. `service.status`, `storage.usage`,
  `network.port_status`, `network.connectivity`, `system.temperature`,
  `manifest.read` y `logs.read` ya son reales (`orchestrator/dispatch.py`);
  `process.list` y `update.pending` quedan para una
  entrega posterior.
- **Fase 4 - Propuestas y evidencia.** Generación real de
  `MaintenanceProposal` y `EvidenceBundle`, escalando hacia el futuro rol
  de Developer Node de HYDRA-UMC-DEV-SERVER.
- **Fase 5 - Interfaz de usuario.** Una API local integrada en
  HYDRA-UMC-SERVER/Studio, luego una CLI, luego voz - nunca sorteando los
  límites de política y confirmación que la Fase 0 ya establece.

Las Fases 1, 2, 4 y 5 no existen todavía en este repositorio, y la propia
Fase 3 está solo parcialmente hecha - ver
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para lo que cada fase
incluye y excluye explícitamente, y
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) para los invariantes de
seguridad que cada fase debe seguir respetando.

## 🔗 Proyectos Relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlos, ya que una petición podría en realidad tratarse de uno de estos en vez de este repositorio.

**Directamente Relacionados**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — el propio padre de este proyecto: el hub de integración del pipeline cognitivo Hailo-10 sobre el que correrá el futuro motor de inferencia de este técnico.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — es dueño del ciclo de vida de incidencias de mantenimiento (evidencia, diagnóstico, cambio aprobado por humano, despliegue canario, verificación); el propio `knowledge/redaction.py` de este técnico es un port directo de su ya probado `log_redaction.py`, y una fase futura escala paquetes de evidencia reales hacia él, sin saltarse jamás su propio flujo de aprobación.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — el futuro Developer Node al que una fase posterior enviará un `EvidenceBundle` real para estudiarlo, probarlo y preparar un parche revisado - nunca un canal directo y automático de parcheo.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — definirá los contratos compartidos y versionados con los que los propios `contracts/*.schema.json` locales de este proyecto están pensados para reconciliarse, en cuanto también existan ahí.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — el futuro punto de entrada autenticado que alojará el propio endpoint, sesiones, roles y rastro de auditoría de este técnico.

**También Parte del Ecosistema**

*Núcleo de Hardware y Plataforma*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la placa base física del brazo robótico: host CM5 + STM32H745 de doble núcleo, orquestando hasta 8 brazos-herramienta por CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — capa de producto reproducible de Raspberry Pi OS para la CM5: agente de solo lectura, config/perfiles validados, aprovisionamiento WiFi de primer contacto.

*Backend Principal y Clientes*
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — panel de control web con visualización 3D multi-robot en tiempo real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de mando de escritorio (PySide6) para varios servidores a la vez.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app de control nativa Android con login biométrico y un compañero Wear OS emparejado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control iOS/iPadOS (Flutter) con sincronización WebSocket en tiempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla DSI de 7" a bordo, embebida en la propia CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de URDF de escritorio que sube modelos terminados al propio catálogo de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — límite de coordinación para flotas AGV/AMR vía un publicador MQTT VDA 5050 real.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de célula CNC de alto nivel con acceso real a estado/byte de control GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — límite de coordinación para droides con patas/humanoides, con un emisor de comandos real para Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de seguridad de célula láser que lee 3 salvaguardas GPIO reales de llave/recinto/interlock.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador seguro de alto nivel de flujo de placas para pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — límite de coordinación seguro para impresoras 3D Moonraker/Klipper, con comandos de trabajo realmente controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador de seguridad con un transporte ROS 2 rclpy real, importado de forma perezosa.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — límite de coordinación para UAVs con cámara, con un emisor de comandos MAVLink real.

*Plataforma de Herramientas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física Universal Robot Tool Controller, 25+ perfiles de herramienta por bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — herramienta gráfica de escritorio para flashear placas URTC, CAN-OTA además de SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de diagnóstico CAN en vivo de escritorio para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa en navegador a URTC-TESTER vía la Web Serial API, sin instalación local.

*Nodo de Visión IA (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub de integración del pipeline de visión Hailo-8, con una comprobación real de disponibilidad de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación de carga segura por arquitectura/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real + generador de config MediaMTX con un límite de integración HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección real de servocontrol visual basado en posición, con puerta de seguridad según el estado de zona.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — comprobación real de intrusión de zona y solicitud de E-STOP, con exigencia de frescura de calibración.

*Nodo Cognitivo de IA (Hailo-10)*
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de action-tokens y generación de trayectoria para un modelo Visión-Lenguaje-Acción.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + parser de intención) con un relay a Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición de tareas real basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda documental real TF-IDF solo stdlib sobre la propia documentación Markdown de este ecosistema.

*Orquestación y Enjambre*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub de integración con un contrato real de informe de salud gRPC/Protobuf y máquina de estados de misión.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de salud de flota basado en gRPC, con su propio retry/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de trayectoria 3D real basado en RRT con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización de estado CRDT LWW-Element-Map real, probada por propiedades para convergencia multi-célula.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub de integración del motor de gemelo digital, con un contrato real de sincronización de compatibilidad de versiones.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — interlock de seguridad real hardware-in-the-loop que enruta comandos entre simulación y hardware real.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática directa real y validación de límites de junta sobre un subconjunto URDF real.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generador procedural real de escenas 2D con exportación de anotaciones YOLO/COCO.

*Datos y Analítica*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — almacén real de series temporales con sqlite3 con una API HTTP real de ingesta/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detector de anomalías real por FFT + línea base estadística, con monitorización de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidad sobre el histórico de DATALAKE, con exportación CSV reproducible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingesta CAN/WebSocket hacia DATALAKE, con deduplicación de secuencia.

*Pasarela Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub de integración que enlaza con protocolos industriales, con una capa real de lista blanca de comandos/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espacio de direcciones OPC-UA real, verificado con una sesión de cliente de protocolo binario real.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real con autenticación opcional por cliente y ACLs de topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reales `/probe` y `/current` de MTConnect con salida en modo degradado.

*Herramientas Complementarias*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — paneles de Resúmenes Inteligentes y Resalte de Anomalías sobre DATALAKE/ANOMALY-DETECTOR, con un respaldo estadístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, un cliente real y en vivo de la propia API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera WearOS con alertas hápticas reales y un relay de voz al teléfono emparejado.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — catálogo de capacidades de adaptadores externos, GET-only por diseño.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — construye una imagen fresca de la CM5 desde el código fuente, otro hermano de "Ecosystem Operations".
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión Python real para un cabezal de inspección térmica/RGB.

---

## 📚 Documentación y Comunidad

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — propósito, las cinco piezas objetivo, arquitectura objetivo, y relaciones del ecosistema.
- **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)** — los seis niveles de riesgo, reglas de datos/secretos, y el límite real y probado de defensa contra inyección.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando, sus flags, y el contrato de códigos de salida.
- **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — la forma real campo a campo de los cinco contratos.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack técnico y guías de codificación para un pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de foco de seguridad de este proyecto.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

GPL-3.0 (software) / CC BY-SA 4.0 (documentación) - ver [LICENSE.md](LICENSE.md).
