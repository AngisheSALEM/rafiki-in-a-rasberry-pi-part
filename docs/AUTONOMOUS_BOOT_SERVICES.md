# Architecture & Services d'Autodémarrage du Robot Rafiki (Raspberry Pi ↔ Serveur PC)

Ce document décrit le fonctionnement autonome sans intervention humaine du robot **Rafiki**. Au démarrage de la Raspberry Pi, deux ponts de communication s'établissent automatiquement avec le serveur orchestrateur situé sur le PC (`10.20.20.224:7860`).

---

## 1. Vue d'Ensemble de l'Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              PC SERVEUR ORCHESTRATEUR                       │
│                   (10.20.20.224:7860)                       │
│                                                             │
│  - GET  /api/body/next       (File de commandes Arduino)    │
│  - POST /api/body/status     (Rapport de statut Arduino)    │
│  - POST /api/vision/register (Enregistrement caméra Pi)     │
│  - POST /api/vision/upload   (Réception frames caméra)      │
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

## 2. Description des Services d'Autodémarrage (Systemd)

Les trois services ci-dessous sont configurés en tant que services **Systemd User** pour démarrer automatiquement dès l'allumage de la Raspberry Pi (`multi-user.target` / `default.target`).

### Service 1 : Contrôle du Corps & Expressions Arduino (`rafiki-body.service`)
- **Rôle** : Reçoit les requêtes d'expression et de mouvements depuis le serveur et transmet les ordres à l'Arduino Mega via liaison série (`/dev/ttyACM0`).
- **Comportement au démarrage** :
  - Tente de se connecter au serveur `http://10.20.20.224:7860/api/body/next`.
  - En cas d'indisponibilité du réseau ou du serveur, boucle automatiquement avec reTentative sans planter (`Restart=always`).
  - Dès qu'une commande (`set_expression`, `motor_gesture`, `screen_text`) est reçue, elle est envoyée sur l'écran TFT/servomoteurs de l'Arduino.
- **Fichier de service** : `/home/admin/.config/systemd/user/rafiki-body.service`

### Service 2 : Capture Caméra OV5647 (`rpi-vision.service`)
- **Rôle** : Initialise la caméra physique OV5647 et héberge l'API microservice sur le port `8000`.
- **Règle Matérielle Strict** : Utilise exclusivement la caméra physique Raspberry Pi OV5647.
- **Fichier de service** : `/home/admin/.config/systemd/user/rpi-vision.service`

### Service 3 : Pousse-Photos Automatique (`rafiki-vision-pusher.service`)
- **Rôle** : Envoie les photos capturées en temps réel au serveur dès que la connexion est établie.
- **Comportement au démarrage** :
  - Attend le démarrage du réseau et du service caméra local (`http://localhost:8000`).
  - S'enregistre auprès du serveur via `POST http://10.20.20.224:7860/api/vision/register`.
  - Capture et pousse régulièrement les images vers `POST http://10.20.20.224:7860/api/vision/upload`.
- **Fichier de service** : `/home/admin/.config/systemd/user/rafiki-vision-pusher.service`

---

## 3. Installation et Activation des Services

Exécuter les commandes suivantes sur la Raspberry Pi pour activer l'autodémarrage sans intervention humaine :

```bash
# 1. Recharger les fichiers systemd
systemctl --user daemon-reload

# 2. Activer le démarrage automatique au boot
systemctl --user enable rpi-vision.service
systemctl --user enable rafiki-body.service
systemctl --user enable rafiki-vision-pusher.service

# 3. Démarrer les services immédiatement
systemctl --user start rpi-vision.service
systemctl --user start rafiki-body.service
systemctl --user start rafiki-vision-pusher.service

# 4. Vérifier leur statut
systemctl --user status rpi-vision.service rafiki-body.service rafiki-vision-pusher.service
```

---

## 4. Tests Unitaires & Vérification

Tous les composants disposent de tests unitaires dédiés pour s'assurer de leur bon fonctionnement.

### Lancer la suite de tests unitaires complète :

```bash
cd /home/admin/Rafiki
PYTHONPATH=. .venv/bin/pytest tests/
```

**Résultats de la validation** : 32 tests unitaires exécutés avec succès (`32 passed`), couvrant :
1. Les contrôleurs de corps et expressions Arduino (`test_body_controller.py`).
2. Le client LLM et le moteur de secours offline (`test_llm_client.py`, `test_fallback_client.py`).
3. L'API Serveur d'Orchestration et le pont Hardware (`test_server.py`).
4. Le service de streaming d'images automatique (`test_vision_pusher.py`).

### Tester le serveur d'orchestration à la main :
```bash
# Sur le serveur PC
PYTHONPATH=. .venv/bin/python run_orchestrator_server.py --port 7860

# Tester la santé du pont
curl http://10.20.20.224:7860/api/bridge/status
```
