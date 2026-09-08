<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN Banner" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🛡️ Lokaler KI-Techniker mit Richtlinien-Gesteuerten Berechtigungen

<p align="center">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Sprache-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Kern-nur%20stdlib-brightgreen.svg" alt="Nur-stdlib-Kern">
  <img src="https://img.shields.io/badge/Phase-0%20von%206-367BF5.svg" alt="Phase 0 von 6">
</p>

> **Status: v0.0.1, Scaffolding - Phase 0 von 6 (Inventar und
> Sicherheitsgrundlage).** Diese Lieferung definiert die reale
> Risikostufen-Richtlinie (`policy/risk_levels.py`), eine feste
> Werkzeug-Positivliste (`policy/tool_matrix.py`), die fünf realen
> Minimalverträge, gegen die jeder künftige Werkzeugaufruf validieren
> muss (`contracts/*.schema.json` + `contracts.py`), eine reale
> Geheimnis-Schwärzung, portiert aus dem bereits getesteten
> `log_redaction.py` von HYDRA-UMC-OPS-AGENT, sowie das wörtliche
> Austrittskriterium dieser Phase 0 selbst: ein echter adversarialer
> Test, der beweist, dass ein bösartiges abgerufenes Dokument niemals
> einen Werkzeugaufruf auslösen oder ein Geheimnis preisgeben kann. Es
> gibt noch keine Inferenz-Engine, keinen RAG-Index, keine echte
> Werkzeugausführung und keine Integration mit HYDRA-UMC-SERVER - siehe
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für die exakte
> Befehlsoberfläche, die heute existiert.

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

HYDRA-UMC-LOCAL-TECHNICIAN ist eine spezialisierte lokale KI für das
HYDRA-UMC-Ökosystem selbst: Sie beobachtet, erklärt, diagnostiziert und
schlägt Wartung für die eigenen Dienste und Knoten des Ökosystems vor -
sie trainiert niemals ein neues Foundation-Modell und handelt niemals
durch das Generieren von Text. Ihre Zielplattform ist die CM5, mit dem
Hailo-10H-Beschleuniger sobald installiert, aber Phase 0 braucht keines
von beidem: Alles in dieser Lieferung ist reines Python, das reine Daten
validiert.

**Nicht verhandelbares Prinzip:** Die KI erhält niemals Autorität durch
das Generieren einer Antwort. Richtlinie, Berechtigungen und menschliche
Bestätigung entscheiden über jede reale Aktion - niemals die eigenen
Worte des Modells.

Diese Lieferung (Phase 0) bringt vier reale, unabhängig nützliche
Bausteine:

1. **Risikostufen-Richtlinie** (`policy/risk_levels.py`) - sechs
   geordnete Stufen, von `INFORM` bis `PHYSICAL_ACTION`, jede mit einer
   realen, getesteten Richtlinie (kann sie ein Werkzeug lesen, kann sie
   mutieren, erfordert sie Bestätigung, ist sie implementiert). Die
   beiden obersten Stufen sind nur der Vertragsvollständigkeit halber
   deklariert - in diesem Code tatsächlich nirgendwo implementiert.
2. **Werkzeug-Matrix** (`policy/tool_matrix.py`) - eine feste
   Positivliste von neun realen `OBSERVE`-Stufen-Werkzeugnamen. Ein
   Werkzeugname, der in diesem Dictionary fehlt, kann niemals aufgerufen
   werden, Punkt - und jeder darin vorhandene Name hat in dieser
   Lieferung immer noch `implemented=False`.
3. **Reale Verträge** (`contracts/*.schema.json` + `contracts.py`) -
   `ToolRequest`, `ToolResult`, `MaintenanceProposal`, `EvidenceBundle`
   und `PatchVerificationReport`, Feld für Feld aus dem eigenen privaten
   Entwicklungsplan dieses Projekts kopiert, jeweils mit einer
   normativen JSON-Schema-Datei und einem passenden, nur auf der Standard-
   bibliothek basierenden Python-Validator.
4. **Injection-Abwehrgrenze** (`knowledge/trust.py` +
   `knowledge/redaction.py`) - nicht vertrauenswürdiger Inhalt (ein
   README, eine Log-Zeile, eine Commit-Nachricht) wird immer als
   `UntrustedText` eingehüllt, ein Typ ohne jede Methode, die jemals
   einen Werkzeugaufruf erzeugen könnte. Der einzige reale Weg, eine
   `ToolRequest` zu konstruieren, nimmt bereits typisierte, bereits
   getrennte Felder entgegen und verweigert jeden nicht registrierten
   oder nicht implementierten Werkzeugnamen, bevor das Objekt überhaupt
   existiert.

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

In dieser Lieferung gibt es weder einen Standard-/argumentlosen Aufruf
noch eine grafische Oberfläche - siehe
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für die vollständige,
reale Befehlsoberfläche.

## 2. 🧱 ARCHITEKTUR UND DESIGN-ENTSCHEIDUNGEN

- **Die KI erhält niemals Autorität durch das Generieren einer
  Antwort.** Jede Design-Entscheidung dieser Lieferung existiert, um
  genau dieses eine Prinzip zu schützen - siehe
  [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) für das vollständige
  Modell.
- **Ein Werkzeug muss registriert sein, bevor es jemals aufgerufen
  werden kann.** `TOOL_MATRIX` in `policy/tool_matrix.py` ist die
  vollständige, feste Liste; dass `lookup_tool()` `None` zurückgibt, ist
  eine bedingungslose Ablehnung, niemals ein Fall, in dem eine
  Standard-Risikostufe geraten wird.
- **Nicht vertrauenswürdiger Inhalt kann niemals zu einem Befehl
  werden.** Die Abwehr ist architektonisch (ein Typ ohne jede Methode,
  die ein Werkzeug erzeugt), kein Filter, der versucht,
  "anweisungsähnlichen" Text zu erkennen - ein von vornherein
  aussichtsloses Spiel gegen eine entschlossene Prompt-Injection. Siehe
  `tests/adversarial/test_injection_defense.py`, das wörtliche
  Austrittskriterium dieser Phase 0 selbst.
- **Die normative Quelle eines Vertrags ist seine JSON-Schema-Datei.**
  Die Feldlisten und Validatoren in `contracts.py` werden Feld für Feld
  aus `contracts/*.schema.json` kopiert, nach derselben Konvention wie
  `validation.py` von HYDRA-UMC-SDK - keine zweite, unabhängige
  Wahrheitsquelle.
- **Die Geheimnis-Schwärzung nutzt bereits getesteten Code wieder.**
  `knowledge/redaction.py` ist eine Byte-für-Byte-Portierung (nur der
  Kopfkommentar unterscheidet sich) des bereits getesteten
  `log_redaction.py` von HYDRA-UMC-OPS-AGENT - das zugrunde liegende
  Problem (reale, wohlbekannte Geheimnisformen ohne eine unscharfe
  Heuristik erkennen) ist hier identisch.
- **`PRIVILEGED_CHANGE` und `PHYSICAL_ACTION` bleiben nicht
  implementiert.** Ein bewusstes, dauerhaftes Tor, bis ein dediziertes
  Design, ein separater Autorisierungspfad und, für physische Aktion,
  echte Verriegelungen existieren - kein Versehen, das später
  nachgeholt wird.
- **Diese Lieferung deklariert und validiert nur - sie handelt noch
  nicht.** Es existiert nirgendwo in diesem Repository eine
  Inferenz-Engine, ein RAG-Index, eine echte Werkzeugausführung oder
  eine Integration mit HYDRA-UMC-SERVER.

## 📂 VERZEICHNISSTRUKTUR

```
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/
│   ├── policy/
│   │   ├── risk_levels.py    # RiskLevel + RiskLevelPolicy: die sechs Stufen, reale Richtlinie pro Stufe
│   │   └── tool_matrix.py    # TOOL_MATRIX: die feste, reale Werkzeug-Positivliste (9 OBSERVE-Namen)
│   ├── knowledge/
│   │   ├── redaction.py      # Reale Geheimnis-Schwärzung, portiert aus HYDRA-UMC-OPS-AGENT
│   │   └── trust.py          # UntrustedText + build_tool_request_from_model_output(): die Injection-Abwehrgrenze
│   ├── contracts.py           # Realer, nur-stdlib Validator für die fünf Minimalverträge
│   └── cli.py                 # Subbefehl contracts validate + --version
├── contracts/                  # Normative JSON-Schema-Dateien (Draft 2020-12) für die fünf Verträge
├── tests/
│   ├── unit/                   # Reale Tests für jedes obige Modul
│   ├── adversarial/            # test_injection_defense.py - das wörtliche Austrittskriterium dieser Phase 0 selbst
│   └── fixtures/                # Gültige/ungültige JSON-Fixtures für jeden Vertrag
├── docs/
│   ├── ARCHITECTURE.md         # Zweck, die fünf Zielbausteine, Zielarchitektur, Ökosystem-Beziehungen
│   ├── SECURITY_MODEL.md       # Die sechs Risikostufen, Daten-/Geheimnisregeln, Injection-Abwehr
│   ├── CLI_REFERENCE.md        # contracts validate, Flags, Exit-Codes
│   └── CONTRACTS.md            # Die reale, feldweise Form aller fünf Verträge
├── images/                      # Medien und App-Icons
├── build.sh / build.bat        # venv + editierbare Installation + Prüfung + Tests
├── build-test.sh / .bat        # Nur nicht-mutierende Build-Validierung
├── run.sh / run.bat            # Leitet einen realen CLI-Befehl weiter
├── bump_version.py             # Ökosystemweiter "Kilometerzähler"-Versionssprung (pyproject.toml + __init__.py)
└── bump_manifest_version.py    # Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
```

## ⚙️ BUILD- UND AUSFÜHRUNGSANLEITUNG

```bash
chmod +x build.sh   # einmalig
./build.sh          # erstellt .venv, pip install -e ".[dev]", Prüfung + Tests
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

Unter Windows: `build.bat`, dann `run.bat contracts validate ...` /
`run.bat --version`. `build-test.sh`/`.bat` führt dieselbe nicht-
mutierende Python-Syntaxprüfung aus, die auch der eigene CI-Workflow
dieses Projekts ausführt, ohne die Projektversion oder das CHANGELOG
anzurühren - sie führt NICHT die Testsuite aus; führe
`./build.sh`/`build.bat` (oder direkt `pytest tests/`) für die
vollständige lokale Testsuite aus.

**Fehlerbehebung**

- `contracts validate` beendet sich mit Code `1` und `INVALID: ...`:
  lies die Meldung - sie nennt das genaue Feld und den Grund, nicht nur,
  dass etwas fehlgeschlagen ist. Siehe
  [docs/CONTRACTS.md](docs/CONTRACTS.md) für die reale, erwartete Form
  jedes der fünf Verträge.
- Ein Test in `tests/adversarial/` schlägt fehl: Das ist das wörtliche
  Austrittskriterium dieser Phase 0 selbst - behandle jeden dortigen
  Fehlschlag als echte Regression der Injection-Abwehrgrenze, niemals
  als einen zu lockernden Test.

## 🚀 ROADMAP

Diese Version bringt nur Phase 0. Was verbleibt, in der Reihenfolge des
eigenen privaten Entwicklungsplans dieses Projekts:

- **Phase 1 - Abrufbares Wissen.** Ein lokaler, versionierter Index
  genehmigter Dokumentation, Manifeste, Verträge und Runbooks - niemals
  blind auf der gesamten Festplatte trainiert.
- **Phase 2 - Lokale Inferenz-Engine.** Ein kleines, mit Hailo-10H
  kompatibles LLM (Kandidaten: Qwen2.5-1.5B-Instruct,
  Qwen2.5-Coder-1.5B, Qwen3-1.7B-Instruct), erst gewählt, nachdem die
  reale Hailo-Kompatibilität, Latenz, Sprachqualität, Leistungsaufnahme
  und Lizenz verifiziert sind.
- **Phase 3 - Werkzeug-Orchestrator.** Deterministischer Code, der die
  ersten realen `OBSERVE`-Stufen-Werkzeug-Handler mit `TOOL_MATRIX`
  verbindet, mit Richtliniendurchsetzung bei jedem Aufruf.
- **Phase 4 - Vorschläge und Nachweise.** Reale Erzeugung von
  `MaintenanceProposal` und `EvidenceBundle`, eskalierend hin zur
  künftigen Developer-Node-Rolle von HYDRA-UMC-DEV-SERVER.
- **Phase 5 - Benutzeroberfläche.** Eine lokale API, integriert in
  HYDRA-UMC-SERVER/Studio, dann eine CLI, dann Sprache - ohne jemals die
  von Phase 0 bereits etablierten Richtlinien- und Bestätigungsgrenzen
  zu umgehen.

Nichts davon existiert bisher in diesem Repository - siehe
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) dafür, was jede Phase
einschließt und explizit ausschließt, und
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) für die
Sicherheitsinvarianten, die jede Phase weiterhin einhalten muss.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage sich eigentlich auf eines dieser Projekte statt auf dieses Repository beziehen könnte.

**Direkt Verwandt**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — der eigene Elternteil dieses Projekts: der Integrations-Hub für die Hailo-10-Kognitiv-Pipeline, auf der die künftige Inferenz-Engine dieses Technikers laufen wird.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — besitzt den Lebenszyklus von Wartungsvorfällen (Nachweis, Diagnose, menschlich genehmigte Änderung, Canary-Deployment, Verifizierung); das eigene `knowledge/redaction.py` dieses Technikers ist eine direkte Portierung seines bereits getesteten `log_redaction.py`, und eine künftige Phase eskaliert reale Nachweispakete zu ihm hin, ohne jemals seinen eigenen Genehmigungsablauf zu umgehen.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — der künftige Developer Node, an den eine spätere Phase ein reales `EvidenceBundle` zur Untersuchung, zum Testen und zur Vorbereitung eines geprüften Patches sendet - niemals ein direkter, automatischer Patch-Kanal.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — wird die gemeinsamen, versionierten Verträge definieren, mit denen die eigenen lokalen `contracts/*.schema.json` dieses Projekts abgeglichen werden sollen, sobald sie dort ebenfalls existieren.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — der künftige authentifizierte Einstiegspunkt, der den eigenen Endpunkt, Sitzungen, Rollen und die Audit-Spur dieses Technikers hosten wird.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware und Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das physische Motherboard des Roboterarms: CM5-Host + STM32H745 Dual-Core, der bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA orchestriert.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für die CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Erstkontakt-Provisioning.

*Kern-Backend und Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das echte, kopflose Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-Multi-Roboter-3D-Visualisierung.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-(PySide6)-Schwarm-Kommandozentrale für mehrere Server gleichzeitig.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischer Anmeldung und einem gekoppelten Wear-OS-Begleiter.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für den eingebauten 7"-DSI-Touchscreen, direkt auf der CM5 eingebettet.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in den eigenen Katalog von STUDIO überträgt.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsgrenze für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — CNC-Zellen-Koordinator auf hoher Ebene mit echtem GRBL-Status-/Steuerbyte-Zugriff.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsgrenze für Lauf-/humanoide Droiden mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, der 3 echte Schlüssel-/Gehäuse-/Interlock-GPIO-Sicherungen liest.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer Koordinator auf hoher Ebene für den Board-Fluss bei OpenPnP-Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsgrenze für Moonraker-/Klipper-3D-Drucker mit real kontrollierten Auftragsbefehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, lazy importierten rclpy-ROS-2-Transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsgrenze für kameraausgestattete UAVs mit einem echten MAVLink-Befehlssender.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — grafisches Desktop-Flash-Tool für URTC-Platinen, CAN-OTA plus vollständiges SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrations-Hub für die Hailo-8-Vision-Pipeline, mit einer echten Hardware-Bereitschaftsprüfung pro Stufe.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echtes Register kompilierter Modelle mit Hailo-Architektur-/Checksummen-Sicherheitsprüfung beim Laden.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echte GStreamer-Pipeline + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsgrenze.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes positionsbasiertes Visual-Servoing-Korrekturgesetz, sicherheitsgesteuert über den Zustand vorgelagerter Zonen.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und E-STOP-Anforderung, mit Durchsetzung der Kalibrierungsaktualität.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Action-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungspflichtigen Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur-stdlib TF-IDF-Dokumentensuche über die eigene Markdown-Dokumentation dieses Ökosystems.

*Orchestrierung und Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrations-Hub mit einem echten gRPC/Protobuf-Gesundheitsbericht-Vertrag und Missions-Zustandsmaschine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Warteschlange mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Gesundheits-Watchdog mit eigenem Retry/Backoff und Identitätsabweichungs-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisierung, eigenschaftsgetestet für Multi-Zellen-Konvergenz.

*Digitaler Zwilling und Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrations-Hub für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Synchronisierungsvertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echter Hardware-in-the-Loop-Sicherheits-Interlock, der Befehle zwischen Simulation und echter Hardware routet.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzen-Validierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten und Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Query-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN-/WebSocket-Ingest-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrielles Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrations-Hub, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Positivlisten-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Sitzung.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Ausgabe im degradierten Modus.

*Ergänzende Werkzeuge*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, einem echten Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — externer Adapter-Fähigkeitskatalog, per Design nur GET.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — baut ein frisches CM5-Image aus dem Quellcode, ein weiterer Geschwisterprojekt aus "Ecosystem Operations".
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinen-Montagerack mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.

---

## 📚 Dokumentation und Community

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Zweck, die fünf Zielbausteine, Zielarchitektur, und Ökosystem-Beziehungen.
- **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)** — die sechs Risikostufen, Daten-/Geheimnisregeln, und die echte, getestete Injection-Abwehrgrenze.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — jeder Subbefehl, seine Flags, und der Exit-Code-Vertrag.
- **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — die reale, feldweise Form aller fünf Verträge.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technik-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

GPL-3.0 (Software) / CC BY-SA 4.0 (Dokumentation) - siehe [LICENSE.md](LICENSE.md).
