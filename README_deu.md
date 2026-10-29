<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - Local, policy-gated maintenance assistant
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN banner" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🛡️ Lokaler KI-Techniker mit Richtlinien-Gesteuerten Berechtigungen

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Phase-1%2C%203%20%26%204%20of%206%20complete-367BF5.svg" alt="Phase">
  <img src="https://img.shields.io/badge/Tests-315%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

- **Phase 5 - Schreibgeschützte lokale API und Webseite (zweite Scheibe).** `serve` (`webapi.py`, `webui/`) zeigt, was der Techniker bereits erzeugt hat: das Werkzeugregister, die ToolResult-, EvidenceBundle- und MaintenanceProposal-Dateien eines Datenverzeichnisses, die Projekt-Manifeste und den Dokumentindex der freigegebenen Wissensquellen. Sie beantwortet nur GET (jede andere Methode erhält 405), bindet an `127.0.0.1`, sofern nichts anderes angegeben ist, und verlangt dann ein Bearer-Token mit mindestens 24 Zeichen, findet Einträge durch Auflisten ihrer Ordner (nie durch Zusammensetzen eines Anfragepfads), schwärzt jede Antwort wie die CLI und begrenzt alle Größen. Die einzelne Seite braucht nichts aus dem Internet und ist auf Englisch, Spanisch, Deutsch, Französisch, Italienisch, Japanisch, Chinesisch und europäischem Portugiesisch verfügbar. Siehe [docs/WEB_API.md](docs/WEB_API.md).

**Ehrlichkeitscheck - was heute wirklich läuft:** die Risikostufen-Richtlinie (`policy/risk_levels.py`), die feste Werkzeug-Zulassungsliste (`policy/tool_matrix.py`), die fünf Vertragsvalidatoren (`contracts.py` + `contracts/*.schema.json`), die Injection-Abwehrgrenze (`knowledge/trust.py`, `knowledge/redaction.py`), der lokale TF-IDF-Wissensindex (`knowledge/index.py`, Phase 1), alle 10 deklarierten OBSERVE-Werkzeuge mit einem echten Handler (`orchestrator/dispatch.py` + `orchestrator/allowlist.py`: `service.status`, `storage.usage`, `network.port_status`, `network.connectivity`, `system.temperature`, `manifest.read`, `logs.read`, `process.list`, `update.pending`, `knowledge.search`), der echte Aufbau von `EvidenceBundle`/`MaintenanceProposal` (`escalation/evidence.py`, `escalation/proposal.py`, Phase 4), und eine echte CLI über alles davon (`tools list`/`tools call`/`escalation evidence`/`escalation propose`, Phase 5's eigene erste Scheibe) sind getestet (315 bestandene Tests plus 149 Subtests über `tests/unit/` und `tests/adversarial/`) - Phase 1, Phase 3 und Phase 4 sind abgeschlossen, Phase 5 ist begonnen. `update.pending` benötigt die optionale Abhängigkeit `hydra-umc-updater` (Extra `update-check`), um GitHub wirklich zu prüfen, und degradiert ehrlich (`available: false`) ohne sie. Es gibt weiterhin keine Inferenz-Engine und keine HYDRA-UMC-SERVER-Integration irgendwo in diesem Repository, und nichts in diesem Code kann bisher auf ein `MaintenanceProposal` einwirken - Phase 2, und der Rest von Phase 5 (die mit HYDRA-UMC-SERVER integrierte API, und Sprache), in der Roadmap weiter unten bleiben vollständig angestrebte Zukunftsarbeit ohne jeglichen Code dahinter. Siehe `CHANGELOG.md` für das, was bisher genau ausgeliefert wurde.

**Signierte Ergebnisse.** Ein `ToolResult` nennt jetzt das `tool`, das es erzeugt hat, und trägt, wenn ein lokaler Schlüssel konfiguriert ist (`HYDRA_UMC_LOCAL_TECHNICIAN_RESULT_KEY` oder `..._FILE` mit einer Datei, 16 Zeichen oder mehr, außerhalb des Repositorys), eine `signature`: HMAC-SHA256 über das kanonische JSON des ganzen Ergebnisses. Beim Bau eines Evidenzpakets wird dann ein unsigniertes, gefälschtes oder für ein anderes Werkzeug vorgelegtes Ergebnis abgelehnt; ohne Schlüssel wird nichts signiert und nichts abgelehnt, wie bisher. Beide Felder sind im Vertrag optional, frühere Ergebnisse bleiben also gültig.

---

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem. Es gibt noch keinen Hardware-E-STOP-Pfad, keine von der Firmware durchgesetzten Grenzen oder Verriegelungen und keinen verifizierten Bewegungsbefehl; Firmware-Images werden mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel geprüft, nicht mit einer asymmetrischen Signatur; TLS und gegenseitiges TLS sind optional und standardmäßig aus; noch keine eigene Platine wurde bestückt oder getestet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

---

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.1.7` |
| Reifegrad | Funktionsfähig |
| Tests | 315 (`python -m pytest -q tests`) |
| Technik | Python 3.11+ / JSON Schema / HailoRT GenAI (optional, later phase) / systemd (cm5 role, Linux only) |
| Ziel | Der Raspberry Pi CM5 einer HYDRA-UMC-Zelle |
| Auf echter Hardware | Noch nicht: für diese Version ist kein Lauf auf echter Hardware vermerkt |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Struktur des Repositorys](#-struktur-des-repositorys) · [Verwandte Projekte](#-verwandte-projekte)

## 🚦 Projektstatus

Jede Zeile ist ein Teil dieses Repositorys, und die Ampel sagt, wie weit er heute ist. Sie beruht auf dem, was das Repository zeigen kann (Tests, Builds, Läufe), nicht auf dem, was geplant ist.

🟢 Fertig und überprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht überprüft · 🔴 Nicht gemacht oder funktioniert nicht

| Bereich | Stand | Was das hier bedeutet |
|---|---|---|
| Software | 🟡 | Funktioniert für seinen Hauptzweck; die Ehrlichkeitsprüfung oben nennt, was noch fehlt |
| Tests | 🟢 | 315 automatische Tests, bei jeder Änderung ausgeführt |
| Echte Hardware | 🔴 | Noch nicht: für diese Version ist kein Lauf auf echter Hardware vermerkt |
| Dokumentation | 🟢 | README in acht Sprachen, bei jeder Änderung gegen das Manifest geprüft |

## 🎯 Überblick

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

Diese Lieferung bringt acht reale, unabhängig nützliche Bausteine:

1. **Risikostufen-Richtlinie** (`policy/risk_levels.py`) - sechs
   geordnete Stufen, von `INFORM` bis `PHYSICAL_ACTION`, jede mit einer
   realen, getesteten Richtlinie (kann sie ein Werkzeug lesen, kann sie
   mutieren, erfordert sie Bestätigung, ist sie implementiert). Die
   beiden obersten Stufen sind nur der Vertragsvollständigkeit halber
   deklariert - in diesem Code tatsächlich nirgendwo implementiert.
2. **Werkzeug-Matrix** (`policy/tool_matrix.py`) - eine feste
   Positivliste von zehn realen `OBSERVE`-Stufen-Werkzeugnamen. Ein
   Werkzeugname, der in diesem Dictionary fehlt, kann niemals aufgerufen
   werden, Punkt - alle 10 sind bereits mit einem echten Handler
   verbunden (siehe Punkte 5 und 6 unten).
3. **Reale Verträge** (`contracts/*.schema.json` + `contracts.py`) -
   `ToolRequest`, `ToolResult`, `MaintenanceProposal`, `EvidenceBundle`
   und `PatchVerificationReport`, jeweils mit einer normativen
   JSON-Schema-Datei und einem passenden, Feld für Feld daraus
   kopierten, nur auf der Standard-
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
5. **Werkzeug-Orchestrator** (`orchestrator/dispatch.py` +
   `orchestrator/allowlist.py`, Phase 3) - `dispatch_tool_request()`
   führt einen bereits validierten `ToolRequest` real aus und liefert
   ein reales `ToolResult`: `service.status` (echtes
   `systemctl is-active`), `storage.usage` (`shutil.disk_usage`),
   `network.port_status` (eine echte Socket-Sonde),
   `network.connectivity` (ein echter HTTP-GET, der den eigenen realen
   Statuscode des Endpunkts meldet - eine tatsächlich andere Prüfung als
   `network.port_status`, dieselbe reale Unterscheidung, die das eigene
   `inventory.py` von HYDRA-UMC-OPS-AGENT bereits zwischen einer reinen
   TCP-Verbindung und einem echten Health-GET zieht), `system.temperature`
   (der reale Linux-Thermalzonen-sysfs-Pfad), `manifest.read` (ein
   echtes Lesen von `hydra-umc.project.json`), `logs.read` (ein
   begrenztes, geschwärztes Ende einer auf der Positivliste stehenden
   Log-Datei), `process.list` (ein echter, auf der Positivliste
   stehender Teilstring-Abgleich gegen `/proc/<pid>/cmdline`), und
   `update.pending` (nutzt die eigene reale GitHub-Erkennung und den
   Versionsvergleich von HYDRA-UMC-UPDATER wieder, optionale
   Abhängigkeit). Keines davon akzeptiert direkt einen rohen
   Pfad/Host/Port/URL/Einheitennamen/Muster - nur einen kurzen
   symbolischen Namen, aufgelöst über ein festes `OrchestratorConfig`,
   sodass der eigene Text eines vergifteten Dokuments niemals ein
   beliebiges reales Ziel benennen kann, sondern nur einen bereits auf
   der Positivliste stehenden Namen.
   Was ein Handler zurückgibt, wird an der Grenze begrenzt und geschwärzt: die Befehlszeile eines Prozesses, ein Wissensauszug und die Logzeilen eines Evidenzpakets durchlaufen dieselbe Geheimnis-Schwärzung wie `logs.read`, `manifest.read` liefert nur vier kurze Zeichenketten, und `network.connectivity` meldet eine Weiterleitung, statt ihr zu folgen.
6. **Abrufbarer Wissensindex** (`knowledge/index.py`, Phase 1) - eine
   reale, lokale TF-IDF-Suchmaschine (tokenize/build_index/search),
   unverändert portiert aus dem bereits getesteten `index.py` von
   HYDRA-UMC-DOCS-QA, plus eine neue begrenzte Aufnahme für
   Markdown-Quellen (nach Überschrift segmentierte Abschnitte) und
   JSON-Quellen (eine ganze Datei pro Abschnitt - ein Manifest oder ein
   Vertragsschema wird niemals sinnvoll mitten im Objekt geteilt).
   Verbunden als zehntes Werkzeug, `knowledge.search`, über das neue
   `resolve_knowledge_source()` von `orchestrator/allowlist.py`: ein
   Aufrufer kann nur eine bereits auf der Positivliste stehende
   symbolische Quelle benennen, niemals einen rohen Pfad, und jeder
   real zurückgegebene Treffer bleibt als `UntrustedText` eingehüllt,
   bevor er den Handler verlässt. Der Durchlauf selbst ist begrenzt
   (Dateianzahl, Dateigröße), selbst für eine legitim auf der
   Positivliste stehende Wurzel - niemals blind, niemals die gesamte
   Festplatte.
7. **Eskalation: Nachweise und Vorschläge** (`escalation/`, Phase 4) -
   `evidence.assemble_evidence_bundle()` wandelt einen realen Stapel
   bereits ausgeführter, bereits validierter `ToolResult`s in ein reales
   `EvidenceBundle` um - nach demselben Muster wie das eigene
   `incident.py` von HYDRA-UMC-OPS-AGENT: reine Ableitung aus bereits
   beobachteten Daten, niemals ein KI-Aufruf. `proposal.propose_maintenance()`
   ist ein realer Konstruktor/Validator für `MaintenanceProposal` -
   bewusst KEIN Generator, da noch keine Inferenz-Engine existiert und
   das nicht verhandelbare Prinzip dieses Projekts das Erfinden einer
   Diagnose ausschließt. Heute liefert nur ein menschlicher Bediener
   `diagnosis`/`steps`/`rollback`; die eine reale Absicherung, die dieses
   Modul zusätzlich hinzufügt, ist, dass jeder Eintrag in
   `citedEvidence` wortwörtlich dem `evidence`-Feld eines real bereits
   beobachteten Werkzeugergebnisses entsprechen muss, sonst wird der
   Vorschlag von vornherein abgelehnt. `confirmationRequired` ist
   niemals vom Aufrufer einstellbar - es ist immer genau das, was die
   Richtlinie in `policy/risk_levels.py` für die deklarierte Risikostufe
   des Vorschlags bereits festlegt. Nichts in diesem Code kann bisher
   auf ein `MaintenanceProposal` einwirken.
8. **CLI-Oberfläche** (`cli.py`, Phase 5's eigene erste reale Scheibe) -
   `tools list`/`tools call` und `escalation evidence`/`escalation
   propose` geben jedem Baustein oben zum ersten Mal eine echte
   Befehlszeile (bisher war jeder von ihnen nur aus einem Test heraus
   erreichbar). Fügt keine eigene Autorität hinzu: `tools call` baut
   einen `ToolRequest` über dasselbe `build_tool_request_from_model_output()`,
   das jeder Test bereits aufruft, und führt ihn über dasselbe
   `dispatch_tool_request()` aus - erreicht weiterhin nur ein
   OBSERVE-Stufen-Werkzeug, da nichts oberhalb von OBSERVE irgendwo in
   diesem Code implementiert ist. `--config` lädt ein reales
   `OrchestratorConfig` aus einer JSON-Datei (oder greift auf
   `default_config()` zurück); es gibt weiterhin keine Möglichkeit,
   einen rohen Pfad/Host/Port direkt auf der Befehlszeile zu nennen.

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

## 🧩 Rolle in HYDRA-UMC

**HYDRA-UMC-LOCAL-TECHNICIAN** ist der lokale Wartungsassistent des Ökosystems: Er beobachtet, erklärt und schlägt vor, und der Text eines Modells ist nie eine Berechtigung zum Handeln. Seine Werkzeuge sind freigegeben und nur lesend, und was er findet, geht als Belege und Vorschläge an Menschen oder an `HYDRA-UMC-OPS-AGENT`.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN architecture" width="100%">
</p>

### ARCHITEKTUR UND DESIGN-ENTSCHEIDUNGEN

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
- **Die Schwärzung von Geheimnissen ist eine gemeinsame Kopie.** `knowledge/redaction.py` ist die von HYDRA-UMC-SDK gepflegte Schwärzung (`tools/canonical/redaction.py`), identisch mit der des Ops-Agenten und gegen dieselben gemeinsamen Fälle geprüft (`tests/redaction_vectors.json`).
- **Jede Tool-Anfrage lässt sich auditieren.** Mit `--audit-log PFAD` (oder `HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG`, oder `auditLog` in der Konfigurationsdatei) wird jede Anfrage vor der Ausführung in ein nur anfügbares JSONL-Journal geschrieben und ihr Ergebnis danach, geschwärzt, jede Zeile per SHA-256 mit der vorigen verkettet, nach Größe rotiert. Eine Anfrage, die sich nicht aufzeichnen lässt, wird nicht ausgeführt; `audit-verify PFAD` prüft die Kette. Standardmäßig aus.
- **`PRIVILEGED_CHANGE` und `PHYSICAL_ACTION` bleiben nicht
  implementiert.** Ein bewusstes, dauerhaftes Tor, bis ein dediziertes
  Design, ein separater Autorisierungspfad und, für physische Aktion,
  echte Verriegelungen existieren - kein Versehen, das später
  nachgeholt wird.
- **Wissensabruf ist begrenzt und auf der Positivliste, niemals
  blind.** `knowledge.search` indiziert nur eine bereits auf der
  Positivliste stehende Wurzel (`resolve_knowledge_source()` von
  `orchestrator/allowlist.py`), und der Durchlauf selbst ist durch eine
  echte Dateianzahl- und Dateigrößengrenze begrenzt - "niemals blind auf
  der gesamten Festplatte trainiert" gilt auch für eine Wurzel, die ein
  Betreiber bereits als sicher eingestuft hat.
- **Diese Lieferung deklariert, ruft ab und validiert nur - sie handelt
  noch nicht.** Es existiert nirgendwo in diesem Repository eine
  Inferenz-Engine, eine echte Werkzeugausführung oberhalb von OBSERVE
  oder eine Integration mit HYDRA-UMC-SERVER.

## 🚀 Schnellstart

Benötigt Python 3.11 oder neuer.

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

## 🧪 Tests

315 automatische Tests laufen mit `python -m pytest -q tests`. Sie brauchen weder Hardware noch etwas außerhalb dieses Rechners.

Die CI führt `HYDRA_UMC_CI=1 python tools/ci_validate.py` aus; das prüft das Manifest, die Dokumente, die acht READMEs und die Bilder.

## 🏗️ Build und Veröffentlichung

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

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-LOCAL-TECHNICIAN" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/   Quellcode
│   ├── policy/                       Werkzeugmatrix, Risikostufen, Ausführungsmodus
│   ├── knowledge/                    Index, Vertrauensstufen, Schwärzung
│   ├── orchestrator/                 Phase 3 + Phase 1 - alle 10 realen OBSERVE-Werkzeug-Handler, vollständig
│   ├── escalation/                   Phase 4 - realer Aufbau von EvidenceBundle + Konstruktion von MaintenanceProposal, vollständig
│   ├── contracts.py                  Realer, nur-stdlib Validator für die fünf Minimalverträge
│   ├── cli.py                        Phase 5 - contracts validate, tools list/call, escalation evidence/propose, --version, serve
│   ├── webapi.py                     schreibgeschützte lokale API: nur GET, standardmäßig Loopback, Token außerhalb von Loopback, geschwärzt und begrenzt
│   └── webui/                        die Offline-Einzelseite: index.html, app.js, app.css und i18n/ in acht Sprachen
├── contracts/                        Normative JSON-Schema-Dateien (Draft 2020-12) für die fünf Verträge
├── tests/                            automatische Tests
├── docs/                             Dokumente des Projekts
├── tools/                            Projektwerkzeuge und CI-Prüfungen
├── images/                           Medien und App-Icons
├── .github/                          CI-Workflow und Issue-Vorlagen
├── build.sh / build.bat              venv + editierbare Installation + Prüfung + Tests
├── run.sh / run.bat                  Leitet einen realen CLI-Befehl weiter
├── bump_version.py                   ausdrückliche Versionserhöhung
├── bump_manifest_version.py          Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
├── CHANGELOG.md                      was sich in jeder Version geändert hat
├── build-test.sh                     Build-Prüfung ohne Änderungen
├── hydra-umc.project.json            Manifest: Version, Reifegrad, Familie
├── pyproject.toml                    Paketmetadaten
└── test.sh                           führt die Tests aus
```

</details>

## 🗺️ Roadmap und bekannte Grenzen

**Bekannte Grenzen heute**

Diese Version bringt Phase 0, Phase 1, Phase 3 und Phase 4. Was in der
Reihenfolge der Phasen verbleibt:

- **Phase 1 - Abrufbares Wissen (abgeschlossen).** Ein lokaler,
  versionierter Index genehmigter Dokumentation, Manifeste, Verträge und
  Runbooks - niemals blind auf der gesamten Festplatte trainiert.
  `knowledge/index.py` portiert unverändert die bereits getestete
  TF-IDF-Suche von HYDRA-UMC-DOCS-QA und fügt eine begrenzte, auf der
  Positivliste stehende Aufnahme für Markdown- und JSON-Quellen hinzu,
  verbunden als zehntes OBSERVE-Stufen-Werkzeug, `knowledge.search`.
- **Phase 2 - Lokale Inferenz-Engine.** Ein kleines, mit Hailo-10H
  kompatibles LLM (Kandidaten: Qwen2.5-1.5B-Instruct,
  Qwen2.5-Coder-1.5B, Qwen3-1.7B-Instruct), erst gewählt, nachdem die
  reale Hailo-Kompatibilität, Latenz, Sprachqualität, Leistungsaufnahme
  und Lizenz verifiziert sind.
- **Phase 3 - Werkzeug-Orchestrator (abgeschlossen: 9 von 9 deklarierten).**
  Deterministischer Code, der alle realen `OBSERVE`-Stufen-
  Werkzeug-Handler mit `TOOL_MATRIX` verbindet, mit
  Richtliniendurchsetzung bei jedem Aufruf. `service.status`,
  `storage.usage`, `network.port_status`, `network.connectivity`,
  `system.temperature`, `manifest.read`, `logs.read`, `process.list` und `update.pending` sind bereits real
  (`orchestrator/dispatch.py`).
- **Phase 4 - Vorschläge und Nachweise (abgeschlossen).** Realer Aufbau
  von `MaintenanceProposal` und `EvidenceBundle` (`escalation/`),
  eskalierend hin zur künftigen Developer-Node-Rolle von
  HYDRA-UMC-DEV-SERVER. `evidence.assemble_evidence_bundle()` leitet ein
  reales Paket aus bereits beobachteten `ToolResult`s ab;
  `proposal.propose_maintenance()` validiert und gründet einen von einem
  Menschen gelieferten Vorschlag gegen reale Nachweise - sie erzeugt ihn
  nie selbst, da noch keine Inferenz-Engine existiert. Nichts in diesem
  Code kann bisher auf ein `MaintenanceProposal` einwirken.
- **Phase 5 - Benutzeroberfläche (begonnen: die CLI-Scheibe).** Eine
  lokale API, integriert in HYDRA-UMC-SERVER/Studio, dann eine CLI, dann
  Sprache - ohne jemals die von Phase 0 bereits etablierten Richtlinien-
  und Bestätigungsgrenzen zu umgehen. Die CLI-Scheibe ist ab jetzt real:
  `tools list`/`tools call` und `escalation evidence`/`escalation
  propose` (`cli.py`) erreichen jeden realen Baustein oben über denselben
  bereits getesteten, bereits richtliniengeprüften Code, bewusst
  begrenzt auf das, was in diesem einen Repository lebt. Die mit
  HYDRA-UMC-SERVER integrierte API und Sprache bleiben separate,
  repoübergreifende Arbeit für eine spätere Lieferung.

Phase 2, und der Rest von Phase 5, existieren noch nicht in diesem Repository - siehe
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) dafür, was jede verbleibende
Phase einschließt und explizit ausschließt, und
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) für die
Sicherheitsinvarianten, die jede Phase weiterhin einhalten muss.

## 🌍 Sprachen

Diese README und die Dokumente des Repositorys gibt es in acht Sprachen: Englisch, Spanisch, Deutsch, Französisch, Italienisch, Japanisch, Chinesisch und Portugiesisch (Portugal). Sie entstehen gemeinsam, und die CI prüft, dass die acht Dateien dieselben Abschnitte und dieselben Links haben. Dieses Repository hat weder eine eigene Oberfläche noch einen eigenen Meldungskatalog, es gibt also keine Oberflächentexte zu übersetzen.

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
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — der Entwurf des Motherboards des Roboterarms: CM5-Host + Dual-Core-STM32H745, gedacht zur Koordination von bis zu 8 Werkzeugarmen über CAN-OTA/SPI-OTA (Firmware in einer frühen Phase; noch keine bestückte Platine).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für die CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Erstkontakt-Provisioning.

*Kern-Backend und Clients*
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-Multi-Roboter-3D-Visualisierung.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-(PySide6)-Schwarm-Kommandozentrale für mehrere Server gleichzeitig.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischer Anmeldung und einem gekoppelten Wear-OS-Begleiter.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für den eingebauten 7"-DSI-Touchscreen, direkt auf der CM5 eingebettet.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in den eigenen Katalog von STUDIO überträgt.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — Desktop-STL-Modelleditor, der echte Teile im selben Modellkatalog transformiert/ersetzt/entfernt/hinzufügt, den auch HYDRA-UMC-EDITOR-URDF bearbeitet.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen VDA-5050-MQTT-Publisher (nur gegen eine emulierte Flotte getestet).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit GRBL-Status-/Steuerbyte-Zugriff (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem Boston-Dynamics-Spot-Befehlssender (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Koordinator für Laserzellen, liest 3 Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Signale (nur gegen einen simulierten Chip getestet; kann keinen Laser scharfschalten oder auslösen).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer Koordinator auf hoher Ebene für den Board-Fluss bei OpenPnP-Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsgrenze für Moonraker-/Klipper-3D-Drucker mit real kontrollierten Auftragsbefehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Koordinator mit einem träge importierten rclpy-ROS-2-Transport (noch nicht gegen eine ROS-2-Installation ausgeführt).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem MAVLink-Befehlssender (nur gegen einen Emulator getestet).

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — grafisches Desktop-Flash-Tool für URTC-Platinen, CAN-OTA plus vollständiges SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — Gateway vor dem CAN-Bus von URTC: Liste erlaubter Kennungen, Ratenbegrenzung und Sitzungsschlüssel; Software auf dem Computer getestet, noch nicht an einem echten Bus.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrations-Hub für die Hailo-8-Vision-Pipeline, mit einer echten Hardware-Bereitschaftsprüfung pro Stufe.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echtes Register kompilierter Modelle mit Hailo-Architektur-/Checksummen-Sicherheitsprüfung beim Laden.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echte GStreamer-Pipeline + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsgrenze.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based-Visual-Servoing-Korrekturgesetz mit Freigabe abhängig vom Zonenstatus; noch keine Posenschätzung per Kamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0-Logik für Zonenverletzung, Kalibrierungsaktualität und E-STOP-Anforderung, die Objektpositionen aus einer Datei nimmt; kein Detektor speist sie, und noch kein physischer E-STOP ist angeschlossen.

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
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — Hardware-in-the-Loop-Router mit einer Software-Kollisionsverriegelung zwischen Simulation und echter Hardware (ohne echte Hardware getestet).
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit haptischen Alarmmustern und einem Sprach-Relay zum gekoppelten Telefon (noch nicht auf einer physischen Uhr ausgeführt).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — externer Adapter-Fähigkeitskatalog, per Design nur GET.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — baut ein frisches CM5-Image aus dem Quellcode, ein weiterer Geschwisterprojekt aus "Ecosystem Operations".
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinen-Montagerack mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.

## 📚 Dokumentation

Hier steht mehr:

* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Zweck, die fünf Zielbausteine, Zielarchitektur, und Ökosystem-Beziehungen.
* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — jeder Subbefehl, seine Flags, und der Exit-Code-Vertrag.
* **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — die reale, feldweise Form aller fünf Verträge.
* [Sicherheitsgrundlage des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Bedrohungsmodell des Ökosystems](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Änderungsprotokoll dieses Repositorys](CHANGELOG.md)
* [Lizenz dieses Repositorys](LICENSE.md)

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (oder `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`) aus: Es muss `CI_VALIDATION=PASS` ausgeben. Führe dafür nicht `build.sh` oder `build.bat` aus; Bauen ist keine Prüfung.
* Die acht READMEs entstehen aus einer einzigen Quelle in HYDRA-UMC-DOCS; bearbeite sie nicht von Hand. Ändere die Quelle und schreibe sie mit `tools/make_readmes.py` neu.
* Behaupte in einer README nichts, was nicht gelaufen ist: Schreibe „simuliert“ oder „nicht auf Hardware erprobt“, wo das stimmt.
* Siehe [CONTRIBUTING.md](CONTRIBUTING.md), den [Verhaltenskodex](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) und [SUPPORT.md](SUPPORT.md).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - [LICENSE](LICENSE).
