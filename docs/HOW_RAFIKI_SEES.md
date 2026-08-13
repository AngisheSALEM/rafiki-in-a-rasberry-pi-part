# 👁️ Comment Rafiki Arrive à Voir : Architecture du Flux Vidéo et de Capture

Ce document détaille précisément la chaîne d'acquisition vidéo et le pipeline de capture d'image mis en place pour permettre à l'agent orchestrateur **Rafiki** de "voir" son environnement en temps réel à l'aide de sa caméra physique Raspberry Pi.

---

## 🏗️ L'Architecture du Flux en 5 Étapes

Voici le cheminement complet d'une image, du capteur physique jusqu'à l'analyse par le modèle de vision :

```mermaid
graph TD
    %% Couches physiques et système
    subgraph Couche Matérielle et Système
        A[Caméra physique CSI OV5647] -->|Flux RAW| B(rpicam-vid)
        B -->|MJPEG Pipe| C(ffmpeg)
        C -->|Écrit dans| D[Périphérique Virtuel /dev/video10]
    end

    %% Services de diffusion et API
    subgraph Services Actifs (Raspberry Pi)
        D -->|Lecture OpenCV| E[Serveur FastAPI - Port 8000]
        E -->|Expose| F[Flux Live HTTP /stream]
        E -->|Expose| G[Endpoint Capture /capture/json]
    end

    %% Consommateurs
    subgraph Consommateurs et Visualisation
        F -->|Lecture par ffplay| H[voir_camera.sh (Affichage Écran)]
        G -->|Appel REST| I[Agent Orchestrateur / Client SDK]
        I -->|Envoi Base64| J[Modèle LLM Vision (Gemini / GPT-4o)]
    end

    classDef hardware fill:#f9f,stroke:#333,stroke-width:2px;
    classDef system fill:#bbf,stroke:#333,stroke-width:2px;
    classDef api fill:#bfb,stroke:#333,stroke-width:2px;
    classDef client fill:#fbb,stroke:#333,stroke-width:2px;

    class A hardware;
    class B,C,D system;
    class E,F,G api;
    class H,I,J client;
```

---

## 📝 Description Détaillée des Composants

### 1. La Caméra Physique (CSI OV5647)
La caméra est connectée en natif sur le port CSI du Raspberry Pi. Le système charge le module matériel spécifique via la configuration `/boot/firmware/config.txt` (`dtoverlay=ov5647,cam1`).

### 2. Le Pont Caméra Virtuel (`ov5647-webcam.service`)
Pour permettre à plusieurs applications ou navigateurs de lire le flux de la caméra sans bloquer le matériel (qui n'accepte qu'un seul lecteur exclusif), un pont virtuel est créé en arrière-plan :
- **`rpicam-vid`** capture le flux de la caméra matérielle 0.
- Le flux est injecté dans **`ffmpeg`**, qui écrit les images en temps réel dans le pilote de boucle vidéo **`v4l2loopback`** sur le périphérique virtuel `/dev/video10`.

### 3. Le Serveur API de Vision (`rpi-vision.service`)
Un serveur FastAPI léger tourne en arrière-plan sur le port **8000** :
- Il est configuré pour lire le flux vidéo virtuel depuis `/dev/video10` via **OpenCV** (à l'aide de l'index de caméra `10` configuré dans le fichier `.env`).
- Il expose des endpoints optimisés, notamment :
  - `/capture/json` : Capture une frame à la demande, l'encode en Base64 et la formate en **Data URI JSON** directement utilisable par les modèles d'intelligence artificielle de vision.
  - `/stream` : Diffuse un flux vidéo **MJPEG** en continu.

### 4. Le Script de Visualisation Locale (`voir_camera.sh`)
Placé sur votre bureau, ce script permet d'ouvrir une fenêtre de prévisualisation en direct sur l'écran du Raspberry Pi :
- Au lieu de lancer `rpicam-vid` en direct (ce qui bloquerait le matériel et empêcherait l'API de fonctionner), il se connecte intelligemment au flux HTTP de l'API (`http://localhost:8000/stream`) à l'aide de **`ffplay`**.
- Cela garantit une visualisation fluide à 30 FPS tout en laissant l'API libre de capturer des photos pour Rafiki.

### 5. L'Orchestrateur et le Modèle LLM Vision
Quand l'agent orchestrateur a besoin de "voir", il procède ainsi :
1. Il appelle le outil d'image en faisant une requête HTTP `GET` sur `http://localhost:8000/capture/json`.
2. Le serveur API extrait la dernière image de `/dev/video10`, l'encode en Base64 et la renvoie instantanément.
3. L'orchestrateur injecte le payload Base64 dans son message destiné au modèle de vision (ex: Gemini/Claude/GPT), qui analyse alors l'image pour répondre aux instructions.

---

## ⚡ Démarrage Rapide

Pour tout démarrer et afficher la caméra, utilisez la commande simplifiée :
```bash
camgo
```
Puis, pour afficher le retour sur votre écran :
```bash
./voir_camera.sh
```
ou double-cliquez sur le raccourci **voir_camera.sh** sur le Bureau !
