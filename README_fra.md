<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="Bannière HYDRA-UMC-LOCAL-TECHNICIAN" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🛡️ Technicien IA Local à Permissions Contrôlées par Politique

<p align="center">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Langage-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Noyau-stdlib%20uniquement-brightgreen.svg" alt="Noyau stdlib uniquement">
  <img src="https://img.shields.io/badge/Phase-3%20sur%206-367BF5.svg" alt="Phase 3 sur 6">
</p>

> **Statut : v0.0.2, fonctionnel - Phase 3 sur 6, partielle
> (orchestrateur d'outils).** La Phase 0 a défini la politique réelle de
> niveaux de risque (`policy/risk_levels.py`), une liste blanche fixe
> d'outils (`policy/tool_matrix.py`), les cinq contrats minimaux réels
> que tout futur appel d'outil devra valider
> (`contracts/*.schema.json` + `contracts.py`), une réelle occultation de
> secrets portée depuis le `log_redaction.py` déjà testé de
> HYDRA-UMC-OPS-AGENT, et le critère de sortie littéral de la Phase 0
> elle-même : un vrai test contradictoire prouvant qu'un document
> malveillant récupéré ne peut jamais déclencher un appel d'outil ni
> divulguer un secret. La Phase 3 connecte 5 des 9 outils OBSERVE
> déclarés à un gestionnaire réel (`orchestrator/dispatch.py`) :
> `service.status`, `storage.usage`, `network.port_status`,
> `system.temperature` et `manifest.read` - chacun ne résolvant qu'un
> nom symbolique sur liste blanche (`orchestrator/allowlist.py`), jamais
> un chemin/hôte/port brut qu'un document récupéré pourrait fournir.
> Aucun moteur d'inférence, aucun index RAG, et aucune intégration
> avec HYDRA-UMC-SERVER n'existent encore - voir
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) pour la surface de
> commandes exacte qui existe aujourd'hui.

---

**Vérification d'honnêteté - ce qui fonctionne réellement aujourd'hui :** la politique de niveaux de risque (`policy/risk_levels.py`), la liste fixe d'outils autorisés (`policy/tool_matrix.py`), les cinq validateurs de contrat (`contracts.py` + `contracts/*.schema.json`), la frontière de défense contre l'injection (`knowledge/trust.py`, `knowledge/redaction.py`), et désormais les 5 premiers gestionnaires réels d'outils OBSERVE (`orchestrator/dispatch.py` + `orchestrator/allowlist.py` : `service.status`, `storage.usage`, `network.port_status`, `system.temperature`, `manifest.read`) sont tous réels et testés (85 tests plus 28 sous-tests passants entre `tests/unit/` et `tests/adversarial/`). Les 4 autres outils de `TOOL_MATRIX` (`process.list`, `network.connectivity`, `update.pending`, `logs.read`) restent `implemented=False` volontairement - chacun nécessite sa propre conception séparée (filtrage, occultation, ou une réelle intégration avec HYDRA-UMC-UPDATER), pas un oubli. Il n'y a toujours aucun moteur d'inférence, aucun index RAG, et aucune intégration avec HYDRA-UMC-SERVER nulle part dans ce dépôt - les Phases 1, 2, 4 et 5 de la feuille de route ci-dessous restent entièrement aspirationnelles, sans aucun code derrière, et la Phase 3 elle-même est partielle (5 outils sur 9). Voir `CHANGELOG.md` pour ce qui a été livré exactement jusqu'à présent.

---

## 1. 🛠️ VUE D'ENSEMBLE TECHNIQUE

HYDRA-UMC-LOCAL-TECHNICIAN est une IA locale spécialisée pour
l'écosystème HYDRA-UMC lui-même : elle observe, explique, diagnostique et
propose la maintenance des services et nœuds de l'écosystème - elle
n'entraîne jamais un nouveau modèle de fondation, et n'agit jamais en
générant du texte. Sa plateforme cible est la CM5, utilisant
l'accélérateur Hailo-10H une fois installé, mais la Phase 0 n'a besoin ni
de l'un ni de l'autre : tout dans cette livraison est du Python pur
validant des données pures.

**Principe non négociable :** l'IA n'obtient jamais d'autorité en
générant une réponse. La politique, les permissions et la confirmation
humaine décident de chaque action réelle - jamais les mots du modèle
lui-même.

Cette livraison (Phase 0) apporte quatre pièces réelles et utiles de
manière indépendante :

1. **Politique de niveaux de risque** (`policy/risk_levels.py`) - six
   niveaux ordonnés, de `INFORM` à `PHYSICAL_ACTION`, chacun avec une
   politique réelle et testée (peut-il lire un outil, peut-il muter,
   requiert-il une confirmation, est-il implémenté). Les deux niveaux
   supérieurs sont déclarés uniquement pour la complétude du contrat -
   véritablement non implémentés nulle part dans ce code.
2. **Matrice d'outils** (`policy/tool_matrix.py`) - une liste blanche
   fixe de neuf noms d'outils réels de niveau `OBSERVE`. Un nom d'outil
   absent de ce dictionnaire ne peut jamais être appelé, point final - et
   chaque nom présent y a encore `implemented=False` dans cette
   livraison.
3. **Contrats réels** (`contracts/*.schema.json` + `contracts.py`) -
   `ToolRequest`, `ToolResult`, `MaintenanceProposal`, `EvidenceBundle`
   et `PatchVerificationReport`, chacun avec un fichier JSON Schema
   normatif et un validateur Python équivalent, stdlib uniquement, copié
   depuis celui-ci champ par champ.
4. **Frontière de défense contre l'injection** (`knowledge/trust.py` +
   `knowledge/redaction.py`) - le contenu non fiable (un README, une
   ligne de log, un message de commit) est toujours enveloppé comme
   `UntrustedText`, un type sans aucune méthode pouvant jamais produire
   un appel d'outil. La seule façon réelle de construire un `ToolRequest`
   prend des champs déjà typés et déjà séparés, et refuse tout nom
   d'outil non enregistré ou non implémenté avant même que l'objet
   n'existe.

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

Il n'y a pas d'invocation par défaut/sans argument ni d'interface
graphique dans cette livraison - voir
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) pour la surface de
commandes réelle et complète.

## 2. 🧱 ARCHITECTURE ET DÉCISIONS DE CONCEPTION

- **L'IA n'obtient jamais d'autorité en générant une réponse.** Chaque
  décision de conception de cette livraison existe pour protéger ce seul
  principe - voir [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) pour
  le modèle complet.
- **Un outil doit être enregistré avant de pouvoir jamais être appelé.**
  `TOOL_MATRIX` de `policy/tool_matrix.py` est la liste complète et
  fixe ; que `lookup_tool()` retourne `None` est un refus inconditionnel,
  jamais un cas où deviner un niveau de risque par défaut.
- **Le contenu non fiable ne peut jamais devenir une commande.** La
  défense est architecturale (un type sans aucune méthode produisant un
  outil), pas un filtre qui tente de reconnaître un texte "ressemblant à
  une instruction" - un jeu perdu d'avance contre une injection de prompt
  déterminée. Voir `tests/adversarial/test_injection_defense.py`, le
  critère de sortie littéral de la Phase 0 elle-même.
- **La source normative d'un contrat est son fichier JSON Schema.** Les
  listes de champs et validateurs de `contracts.py` sont copiés depuis
  `contracts/*.schema.json`, champ par champ, suivant la même convention
  que `validation.py` de HYDRA-UMC-SDK - pas une seconde source de
  vérité indépendante.
- **L'occultation de secrets réutilise du code déjà testé.**
  `knowledge/redaction.py` est un portage octet par octet (seul le
  commentaire d'en-tête change) du `log_redaction.py` déjà testé de
  HYDRA-UMC-OPS-AGENT - le problème sous-jacent (reconnaître des formes
  de secrets réelles et bien connues sans heuristique floue) y est
  identique.
- **`PRIVILEGED_CHANGE` et `PHYSICAL_ACTION` restent non implémentés.**
  Une porte délibérée et permanente jusqu'à ce qu'existent une
  conception dédiée, un chemin d'autorisation séparé et, pour l'action
  physique, de réels verrouillages - pas un oubli à compléter plus tard.
- **Cette livraison ne fait que déclarer et valider - elle n'agit pas
  encore.** Aucun moteur d'inférence, aucun index RAG, aucune exécution
  réelle d'outil, et aucune intégration avec HYDRA-UMC-SERVER n'existent
  nulle part dans ce dépôt pour l'instant.

## 📂 STRUCTURE DES RÉPERTOIRES

```
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/
│   ├── policy/
│   │   ├── risk_levels.py    # RiskLevel + RiskLevelPolicy : les six niveaux, politique réelle par niveau
│   │   └── tool_matrix.py    # TOOL_MATRIX : la liste blanche fixe et réelle d'outils (9 noms OBSERVE)
│   ├── knowledge/
│   │   ├── redaction.py      # Occultation réelle de secrets, portée depuis HYDRA-UMC-OPS-AGENT
│   │   └── trust.py          # UntrustedText + build_tool_request_from_model_output() : la frontière de défense contre l'injection
│   ├── contracts.py           # Validateur réel, stdlib uniquement, pour les cinq contrats minimaux
│   └── cli.py                 # Sous-commande contracts validate + --version
├── contracts/                  # Fichiers JSON Schema normatifs (draft 2020-12) pour les cinq contrats
├── tests/
│   ├── unit/                   # Tests réels pour chaque module ci-dessus
│   ├── adversarial/            # test_injection_defense.py - le critère de sortie littéral de la Phase 0 elle-même
│   └── fixtures/                # Fixtures JSON valides/invalides pour chaque contrat
├── docs/
│   ├── ARCHITECTURE.md         # Objectif, les cinq pièces cibles, architecture cible, relations avec l'écosystème
│   ├── SECURITY_MODEL.md       # Les six niveaux de risque, règles données/secrets, défense contre l'injection
│   ├── CLI_REFERENCE.md        # contracts validate, options, codes de sortie
│   └── CONTRACTS.md            # La forme réelle, champ par champ, des cinq contrats
├── images/                      # Médias et icônes de l'app
├── build.sh / build.bat        # venv + installation éditable + vérification + tests
├── build-test.sh / .bat        # Validation de build non mutante uniquement
├── run.sh / run.bat            # Transmet une commande CLI réelle
├── bump_version.py             # Incrément "compteur kilométrique" de tout l'écosystème (pyproject.toml + __init__.py)
└── bump_manifest_version.py    # Synchronise la version de hydra-umc.project.json avec la native (--sync)
```

## ⚙️ GUIDE DE COMPILATION ET D'EXÉCUTION

```bash
chmod +x build.sh   # une seule fois
./build.sh          # crée .venv, pip install -e ".[dev]", vérification + tests
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

Sous Windows : `build.bat`, puis `run.bat contracts validate ...` /
`run.bat --version`. `build-test.sh`/`.bat` effectue la même vérification
de syntaxe Python non mutante que le propre workflow CI de ce projet,
sans toucher à la version du projet ni au CHANGELOG - elle n'exécute PAS
la suite de tests ; exécutez `./build.sh`/`build.bat` (ou `pytest tests/`
directement) pour la suite de tests locale complète.

**Dépannage**

- `contracts validate` sort avec le code `1` et `INVALID: ...` : lisez le
  message - il nomme le champ exact et la raison, pas seulement que
  quelque chose a échoué. Consultez
  [docs/CONTRACTS.md](docs/CONTRACTS.md) pour la forme réelle attendue
  de chacun des cinq contrats.
- Un test dans `tests/adversarial/` échoue : c'est le critère de sortie
  littéral de la Phase 0 elle-même - traitez tout échec là comme une
  vraie régression de la frontière de défense contre l'injection, jamais
  comme un test à assouplir.

## 🚀 FEUILLE DE ROUTE

Cette version apporte la Phase 0 et une partie de la Phase 3. Ce qui reste, dans l'ordre des
phases :

- **Phase 1 - Connaissance récupérable.** Un index local et versionné de
  documentation, manifestes, contrats et runbooks approuvés - jamais
  entraîné aveuglément sur tout le disque.
- **Phase 2 - Moteur d'inférence local.** Un petit LLM compatible avec
  Hailo-10H (candidats : Qwen2.5-1.5B-Instruct, Qwen2.5-Coder-1.5B,
  Qwen3-1.7B-Instruct), choisi seulement une fois vérifiées la
  compatibilité Hailo réelle, la latence, la qualité linguistique, la
  consommation et la licence.
- **Phase 3 - Orchestrateur d'outils (partielle : 5 sur 9).** Code
  déterministe connectant les premiers gestionnaires réels d'outils de
  niveau `OBSERVE` à `TOOL_MATRIX`, avec la politique appliquée à chaque
  appel. `service.status`, `storage.usage`, `network.port_status`,
  `system.temperature` et `manifest.read` sont déjà réels
  (`orchestrator/dispatch.py`) ; `process.list`, `network.connectivity`,
  `update.pending` et `logs.read` restent pour une livraison ultérieure.
- **Phase 4 - Propositions et preuves.** Génération réelle de
  `MaintenanceProposal` et `EvidenceBundle`, escaladant vers le futur
  rôle de Developer Node de HYDRA-UMC-DEV-SERVER.
- **Phase 5 - Interface utilisateur.** Une API locale intégrée dans
  HYDRA-UMC-SERVER/Studio, puis une CLI, puis la voix - sans jamais
  contourner les limites de politique et de confirmation déjà établies
  par la Phase 0.

Les Phases 1, 2, 4 et 5 n'existent pas encore dans ce dépôt, et la Phase
3 elle-même n'est que partiellement faite - voir
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour ce que chaque phase
inclut et exclut explicitement, et
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) pour les invariants de
sécurité que chaque phase doit continuer à respecter.

## 🔗 Projets Liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Directement Liés**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — le propre parent de ce projet : le hub d'intégration du pipeline cognitif Hailo-10 sur lequel tournera le futur moteur d'inférence de ce technicien.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — propriétaire du cycle de vie des incidents de maintenance (preuve, diagnostic, changement approuvé par un humain, déploiement canari, vérification) ; le propre `knowledge/redaction.py` de ce technicien est un portage direct de son `log_redaction.py` déjà testé, et une phase future escalade de vrais paquets de preuves vers lui, sans jamais contourner son propre flux d'approbation.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — le futur Developer Node vers lequel une phase ultérieure enverra un `EvidenceBundle` réel pour étude, test et préparation d'un correctif révisé - jamais un canal de correction direct et automatique.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — définira les contrats partagés et versionnés avec lesquels les propres `contracts/*.schema.json` locaux de ce projet sont destinés à se réconcilier, une fois qu'ils y existeront aussi.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le futur point d'entrée authentifié qui hébergera le propre endpoint, les sessions, les rôles et la piste d'audit de ce technicien.

**Également Dans l'Écosystème**

*Cœur Matériel et Plateforme*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + STM32H745 double cœur, orchestrant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible Raspberry Pi OS pour la CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi au premier contact.

*Backend Principal et Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande de bureau (PySide6) pour plusieurs serveurs à la fois.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et compagnon Wear OS apparié.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran DSI embarqué de 7", intégrée directement sur la CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui pousse les modèles terminés vers le catalogue de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour flottes AGV/AMR via un vrai éditeur MQTT VDA 5050.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur de cellule CNC haut niveau avec accès réel à l'état/octet de contrôle GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité de cellule laser lisant 3 vraies protections GPIO clé/enceinte/interlock.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur sûr haut niveau du flux de cartes pour pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec des commandes de tâche réellement contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un transport ROS 2 rclpy réel, importé paresseusement.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméras, avec un véritable émetteur de commandes MAVLink.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, 25+ profils d'outils via bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil graphique de bureau pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de diagnostic CAN en direct de bureau pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

*Nœud de Vision IA (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration du pipeline de vision Hailo-8, avec une vérification réelle de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sûr par architecture/checksum Hailo.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer réel + générateur de config MediaMTX avec une véritable frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — loi de correction réelle d'asservissement visuel basé sur la position, protégée selon l'état de zone.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vérification réelle d'intrusion de zone et demande d'E-STOP, avec exigence de fraîcheur de calibration.

*Nœud Cognitif IA (Hailo-10)*
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — encodage/décodage réel de jetons d'action et génération de trajectoire pour un modèle Vision-Langage-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — interface vocale réelle (VAD + analyseur d'intention) avec un relais Watch limité et confirmé.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — décomposition de tâches réelle basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — recherche documentaire réelle TF-IDF stdlib uniquement sur la propre documentation Markdown de cet écosystème.

*Orchestration et Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un contrat réel de rapport de santé gRPC/Protobuf et machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — file d'attente de tâches réelle basée sur la priorité avec déduplication, via une véritable API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — surveillant réel de santé de flotte basé sur gRPC, avec son propre retry/backoff et détection de non-concordance d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificateur de trajectoire 3D réel basé sur RRT avec validation réelle de collision obstacles/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — synchronisation d'état CRDT LWW-Element-Map réelle, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique et Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration du moteur de jumeau numérique, avec un contrat réel de synchronisation de compatibilité de versions.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — interlock de sécurité réel hardware-in-the-loop acheminant les commandes entre simulation et matériel réel.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinématique directe réelle et validation des limites d'articulation sur un sous-ensemble URDF réel.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — générateur procédural réel de scènes 2D avec export d'annotations YOLO/COCO.

*Données et Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — entrepôt réel de séries temporelles avec sqlite3 et une véritable API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — détecteur d'anomalies réel par FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — calcul réel OEE/disponibilité sur l'historique DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline réel d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication de séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration reliant aux protocoles industriels, avec une véritable couche de liste blanche de commandes/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espace d'adressage OPC-UA réel, vérifié avec une véritable session client de protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT réel avec authentification par client optionnelle et ACL de topics.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — véritables points de terminaison XML `/probe` et `/current` MTConnect avec sortie en mode dégradé.

*Outils Complémentaires*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux de Résumés Intelligents et de Mise en Évidence d'Anomalies sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un contrat réel et stable de codes de sortie, un client réel et en direct de la propre API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de véritables alertes haptiques et un relais vocal vers le téléphone apparié.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — catalogue de capacités d'adaptateurs externes, GET uniquement par conception.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — construit une image fraîche de la CM5 depuis les sources, un autre membre d'"Ecosystem Operations".
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un véritable compagnon de vision Python pour une tête d'inspection thermique/RGB.

---

## 📚 Documentation et Communauté

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — objectif, les cinq pièces cibles, architecture cible, et relations avec l'écosystème.
- **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)** — les six niveaux de risque, règles données/secrets, et la véritable frontière testée de défense contre l'injection.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — chaque sous-commande, ses options, et le contrat de codes de sortie.
- **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — la forme réelle, champ par champ, des cinq contrats.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technique et lignes directrices de codage pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les normes de comportement attendues dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables domaines de sécurité prioritaires de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE

GPL-3.0 (logiciel) / CC BY-SA 4.0 (documentation) - voir [LICENSE.md](LICENSE.md).
