# 📘 Architecture & Fonctionnement : Raspberry Pi Vision Service

Ce document explique l'architecture globale et le fonctionnement du microservice **Raspberry Pi Vision Service**, destiné à transformer un Raspberry Pi en un serveur de capture visuelle ultra-rapide et autonome pour les agents IA et modèles LLM (GPT-4o, Claude 3.5, Gemini, Ollama, etc.).

---

## 🎯 1. Principes & Découpage des Rôles

Le système suit une séparation claire des responsabilités :

1. **Le Raspberry Pi (Microservice de Capture Visuelle) :**
   - N'exécute **aucun LLM lourd localement** afin de réserver les ressources du Pi (CPU/RAM).
   - Héberge un serveur **FastAPI** asynchrone et réactif.
   - S'interface avec le matériel vidéo (Caméra officielle CSI `Picamera2`, Webcams USB V4L2/OpenCV, flux RTSP, ou mode Mock pour les tests).
   - Expose des endpoints REST optimisés retournant l'image formatée en **Data URI Base64 JSON** ou en **JPEG/PNG binaire**.

2. **L'Agent Orchestrator / Client LLM (Machine hôte, Cloud ou Agent IA) :**
   - Utilise le SDK Python inclus (`RpiVisionClient`) ou des requêtes HTTP standard.
   - Invoque la capture d'image (`GET /capture/json`).
   - Injecte le résultat Base64 directement dans le prompt du modèle de Vision.

---

## 🏗️ 2. Diagramme d'Architecture & Flux de Données

```text
 ┌────────────────────────────────────────────────────────┐
 │           1. CLIENT / AGENT IA ORCHESTRATEUR           │
 │  - Reçoit une instruction nécessitant une vue réelle  │
 │  - Utilise RpiVisionClient ou fait un appel HTTP       │
 └──────────────────────────┬─────────────────────────────┘
                            │ GET /capture/json (HTTP REST)
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │       2. RASPBERRY PI VISION CAPTURE SERVICE           │
 │  - Tourne sur le Raspberry Pi (FastAPI - Port 8000)   │
 │  - Abstract Camera Factory (V4L2 / Picamera2 / Mock)   │
 │  - Capture la frame & encode en Base64 Data URI        │
 └──────────────────────────┬─────────────────────────────┘
                            │ Réponse JSON ({ "data_uri": "..." })
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │        3. ANALYSE PAR LE MODÈLE LLM VISION             │
 │  - Transmission du Data URI à OpenAI / Claude / Gemini │
 │  - Analyse sémantique et réponse visuelle              │
 └────────────────────────────────────────────────────────┘
```

---

## 📷 3. Détails Techniques du Microservice Raspberry Pi

### A. Abstraction Matérielle (Pattern Factory)
Le module s'adapte automatiquement au matériel disponible via `rpi_vision/camera/factory.py` :
- **Picamera2 (`picam2_cam.py`)** : Pour le module caméra officiel Raspberry Pi CSI via `libcamera`.
- **OpenCV (`opencv_cam.py`)** : Pour les webcams USB (`/dev/video0`) et caméras IP (`rtsp://...`).
- **Mock Simulator (`mock_cam.py`)** : Générateur de mires de test avec horodatage pour le développement sans caméra physique.

### B. Configuration Matérielle (`config.txt`)
Sur Raspberry Pi OS, le fichier [`config.txt`](file:///C:/Users/Salem/Documents/projet/rpi-vision-service/config.txt) configure les overlays matériels nécessaires :
```ini
camera_auto_detect=0
dtoverlay=ov5647,cam1
dtoverlay=audremap,pins_18_19
dtoverlay=seeed-2mic-voicecard
```

### C. Endpoints de l'API REST
- `GET /capture/json` : Capture l'image et la retourne dans une structure JSON idéale pour les LLM Vision (`data_uri`, `mime_type`, `metadata`).
- `GET /capture` : Renvoie l'image brute en binaire (`image/jpeg` ou `image/png`).
- `GET /stream` : Flux vidéo MJPEG en direct pour prévisualisation web.
- `POST /config` : Ajustement dynamique de la résolution, qualité JPEG, rotation (0°, 90°, 180°, 270°) et inversion miroir.
- `GET /health` : État de santé du matériel et configuration active.

---

## 🚀 4. Déploiement & Démarrage Rapide

### Sur le Raspberry Pi :
```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer le serveur (auto-détection de la caméra)
python run_server.py --host 0.0.0.0 --port 8000
```

### Démarrage Automatique (Service Systemd) :
```bash
sudo cp systemd/rpi-vision.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-vision.service
```
