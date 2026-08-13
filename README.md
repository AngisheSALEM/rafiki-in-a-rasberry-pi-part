# 🤖 Robot Compagnon Éducatif Rafiki — Raspberry Pi & Arduino Mega

Bienvenue dans le dépôt principal du projet **Rafiki** (Projet Makers 2026). Ce projet transforme une Raspberry Pi et une carte Arduino Mega 2560 en un robot compagnon expressif et intelligent, capable d'interagir par la parole, la vision par ordinateur et des expressions faciales dynamiques.

---

## 🌟 Vue d'Ensemble de l'Architecture

Le système repose sur une architecture distribuée et résiliente entre la **Raspberry Pi** (embarqué hardware), l'**Arduino Mega** (contrôle écran TFT et servomoteurs) et le **PC Serveur Orchestrateur** (`10.20.20.224:7860`).

```text
┌─────────────────────────────────────────────────────────────┐
│              PC SERVEUR ORCHESTRATEUR                       │
│                   (10.20.20.224:7860)                       │
│                                                             │
│  - GET  /api/body/next       (File de commandes Arduino)    │
│  - POST /api/body/status     (Rapport de statut Arduino)    │
│  - POST /api/vision/register (Enregistrement caméra Pi)     │
│  - POST /api/vision/upload   (Réception des frames photos)  │
│  - POST /api/orchestration/step (Agent Rafiki LLM)          │
└───────────────────────────▲─────────────────────────────────┘
                            │ (Connexion HTTP automatique)
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                     RASPBERRY PI                            │
│                                                             │
│  1. [rafiki-body.service]                                   │
│     `body_pull_client.py` ──> Série /dev/ttyACM0 ──> Arduino  │
│                                                     (Mega)  │
│  2. [rpi-vision.service]                                    │
│     API Vision (Port 8000) ──> Caméra physique OV5647       │
│                                                             │
│  3. [rafiki-vision-pusher.service]                          │
│     `vision_pusher.py` ──> Pousse les photos au PC          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Sous-Systèmes Détaillés

### 1. Contrôle du Corps & Écran TFT Arduino (`body/` & `raspberry/`)
- **Code Arduino** : [`rafiki_mega_expressions_mouvements.ino`](file:///home/admin/Rafiki/rafiki_mega_expressions_mouvements.ino)
  - Reçoit les commandes séries envoyées par la Raspberry Pi sur `/dev/ttyACM0` à 115200 baud.
  - **Expressions faciales TFT (`E0..E9`)** : Joie (`E0`), Tristesse (`E2`), Neutre (`E4`), Réflexion (`E7`), Surprise (`E6`), Encouragement (`E8`).
  - **Mouvements & Servomoteurs (`B0..B9`, `BSTOP`)** : Saluer (`B1`), Danser (`B8`), Hocher la tête (`B7`), Stop (`BSTOP`).
  - **Affichage dynamique de texte (`TEXT:<message>`)** : Affiche directement le texte sur l'écran TFT pour les quiz et les explications.
- **Client Pull Raspberry Pi** : [`raspberry/app/body_pull_client.py`](file:///home/admin/Rafiki/raspberry/app/body_pull_client.py)
  - Interroge régulièrement le serveur via `GET /api/body/next` et transmet les ordres à l'Arduino sans planter en cas de déconnexion.

### 2. Vision & Caméra Physique OV5647 (`rpi_vision/` & `scripts/camgo`)
- **Microservice Caméra** : [`rpi_vision/api/app.py`](file:///home/admin/Rafiki/rpi_vision/api/app.py)
  - S'interface directement avec la **caméra physique OV5647** (port `8000`).
- **Script de démarrage Caméra** : [`scripts/camgo`](file:///home/admin/Rafiki/scripts/camgo)
  - Vérifie la caméra matérielle et relance `/dev/video10` et le service vision.
- **Pousse-photos Automatique** : [`rpi_vision/client/vision_pusher.py`](file:///home/admin/Rafiki/rpi_vision/client/vision_pusher.py)
  - Transmet en continu les images capturées au serveur orchestrateur dès que la liaison réseau est active.

### 3. Serveur Orchestrateur & Pont Hardware (`orchestrator/`)
- **Serveur FastAPI** : [`orchestrator/server.py`](file:///home/admin/Rafiki/orchestrator/server.py) / [`run_orchestrator_server.py`](file:///home/admin/Rafiki/run_orchestrator_server.py)
  - Hébergé sur le PC (`10.20.20.224:7860`).
  - Centralise le LLM Rafiki ([`RafikiLLMClient`](file:///home/admin/Rafiki/orchestrator/services/llm_client.py) / [`FallbackRafikiClient`](file:///home/admin/Rafiki/orchestrator/services/fallback_client.py)).
  - Traduit automatiquement les décisions de l'agent (émotions, gestes, phrases) en commandes synchronisées pour l'Arduino et l'écran.

---

## 🔄 Démarrage Autonome au Boot (Systemd sans intervention humaine)

Trois services Systemd User s'exécutent automatiquement au démarrage de la Raspberry Pi :

```bash
# Activation des services au démarrage
systemctl --user daemon-reload
systemctl --user enable rpi-vision.service
systemctl --user enable rafiki-body.service
systemctl --user enable rafiki-vision-pusher.service

# Démarrer les services immédiatement
systemctl --user start rpi-vision.service rafiki-body.service rafiki-vision-pusher.service
```

Statuts des fichiers de services :
- [`systemd/rpi-vision.service`](file:///home/admin/Rafiki/systemd/rpi-vision.service)
- [`systemd/rafiki-body.service`](file:///home/admin/Rafiki/systemd/rafiki-body.service)
- [`systemd/rafiki-vision-pusher.service`](file:///home/admin/Rafiki/systemd/rafiki-vision-pusher.service)

---

## 📡 Spécification des Endpoints de l'API Pont (Port 7860)

| Méthode | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | État de santé global du serveur et du pont hardware |
| `GET` | `/api/bridge/status` | Rapport de connexion du corps Arduino et de la caméra |
| `GET` | `/api/body/next` | Polled par la Pi pour récupérer la prochaine commande Arduino |
| `POST` | `/api/body/status` | Reçoit le rapport de statut du contrôleur Arduino |
| `POST` | `/api/body/enqueue` | Enfile manuellement une commande d'expression/mouvement |
| `POST` | `/api/vision/register` | Enregistre l'URL du service caméra de la Pi |
| `POST` | `/api/vision/upload` | Reçoit une photo capturée par la Raspberry Pi |
| `GET` | `/api/vision/latest` | Retourne la dernière photo disponible |
| `POST` | `/api/orchestration/step` | Endpoint d'interaction IA qui génère la réponse et pilote l'Arduino |

---

## 🛠️ Guide d'Installation et Exécution

### 1. Installation des dépendances Python
```bash
cd Rafiki
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Exécution de la suite de tests unitaires (32 tests)
```bash
PYTHONPATH=. .venv/bin/pytest tests/
```

### 3. Lancement du Serveur Orchestrateur sur le PC Hôte (Port 7860)
```bash
PYTHONPATH=. .venv/bin/python run_orchestrator_server.py --host 0.0.0.0 --port 7860
```

---

## 📚 Documentation Complémentaire

- 📖 [`docs/AUTONOMOUS_BOOT_SERVICES.md`](file:///home/admin/Rafiki/docs/AUTONOMOUS_BOOT_SERVICES.md) : Guide détaillé de la configuration autonome Systemd.
- 👁️ [`docs/HOW_RAFIKI_SEES.md`](file:///home/admin/Rafiki/docs/HOW_RAFIKI_SEES.md) : Architecture de la vision et intégration de la caméra OV5647.
- 📐 [`docs/ARCHITECTURE_EXPLANATION.md`](file:///home/admin/Rafiki/docs/ARCHITECTURE_EXPLANATION.md) : Explication technique globale du système Rafiki.
