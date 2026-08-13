"""
API Routes for Raspberry Pi Vision Service.
"""
import os
import glob
import logging
from datetime import datetime
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Response
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..camera.base import BaseCamera, FrameData

logger = logging.getLogger("rpi_vision.api")
router = APIRouter()

_camera_instance: Optional[BaseCamera] = None
PHOTOS_DIR = "/home/admin/rafiki-vision-rasberry-pi/captured_photos"

def save_photo_to_disk(frame_bytes: bytes) -> str:
    try:
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(frame_bytes)
        logger.info(f"Saved captured photo to {filepath}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save photo to disk: {e}")
        return ""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rafiki Vision Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0f172a;
            --bg-surface: #1e293b;
            --bg-surface-elevated: #334155;
            --accent-primary: #10b981;
            --accent-primary-hover: #059669;
            --accent-secondary: #3b82f6;
            --accent-danger: #ef4444;
            --accent-danger-hover: #dc2626;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #475569;
            --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: var(--font-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background-color: var(--bg-surface);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            width: 2.25rem;
            height: 2.25rem;
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #0f172a;
            font-size: 1.2rem;
        }

        h1 {
            font-size: 1.25rem;
            font-weight: 600;
            letter-spacing: -0.025em;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--accent-primary);
            padding: 0.375rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .pulse-dot {
            width: 0.5rem;
            height: 0.5rem;
            background-color: var(--accent-primary);
            border-radius: 50%;
            animation: pulse-animation 2s infinite;
        }

        @keyframes pulse-animation {
            0% { transform: scale(0.9); opacity: 0.6; }
            50% { transform: scale(1.15); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.6; }
        }

        main {
            flex: 1;
            padding: 2rem;
            max-width: 1440px;
            width: 100%;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            box-shadow: var(--shadow-lg);
        }

        .panel-title {
            font-size: 1.1rem;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
            margin-bottom: 0.5rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        label {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        select, input[type="text"], input[type="password"] {
            background-color: var(--bg-base);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.625rem 0.875rem;
            border-radius: 0.375rem;
            font-family: inherit;
            font-size: 0.875rem;
            outline: none;
            transition: border-color 0.2s;
        }

        select:focus, input[type="text"]:focus, input[type="password"]:focus {
            border-color: var(--accent-secondary);
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }

        button {
            font-family: var(--font-main);
            font-size: 0.875rem;
            font-weight: 600;
            padding: 0.625rem 1.25rem;
            border-radius: 0.375rem;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background-color: var(--accent-primary);
            color: #0f172a;
        }

        .btn-primary:hover {
            background-color: var(--accent-primary-hover);
        }

        .btn-danger {
            background-color: var(--accent-danger);
            color: white;
        }

        .btn-danger:hover {
            background-color: var(--accent-danger-hover);
        }

        .btn-secondary {
            background-color: var(--bg-surface-elevated);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background-color: var(--border-color);
        }

        /* Gallery Section */
        .gallery-container {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .gallery-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .gallery-actions {
            display: flex;
            gap: 0.75rem;
        }

        .photos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
        }

        .photo-card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: var(--shadow-lg);
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s;
        }

        .photo-card:hover {
            transform: translateY(-2px);
            border-color: var(--accent-secondary);
        }

        .photo-wrapper {
            position: relative;
            aspect-ratio: 16/9;
            background-color: #000;
            overflow: hidden;
            cursor: pointer;
        }

        .photo-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }

        .photo-wrapper:hover img {
            transform: scale(1.05);
        }

        .photo-info {
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            flex-grow: 1;
        }

        .photo-title {
            font-size: 0.875rem;
            font-weight: 600;
            font-family: var(--font-mono);
            word-break: break-all;
        }

        .photo-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .photo-actions {
            margin-top: auto;
            border-top: 1px solid var(--border-color);
            padding: 0.75rem 1rem;
            display: flex;
            justify-content: flex-end;
            gap: 0.5rem;
        }

        .btn-icon-danger {
            background-color: transparent;
            color: var(--accent-danger);
            padding: 0.375rem;
            border-radius: 0.25rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn-icon-danger:hover {
            background-color: rgba(239, 68, 68, 0.1);
        }

        .empty-state {
            grid-column: 1 / -1;
            text-align: center;
            padding: 5rem 2rem;
            background-color: var(--bg-surface);
            border: 2px dashed var(--border-color);
            border-radius: 0.75rem;
            color: var(--text-secondary);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.95);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }

        .modal-content {
            max-width: 90%;
            max-height: 85%;
        }

        .modal-content img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            border-radius: 0.375rem;
        }

        .modal-close {
            position: absolute;
            top: 1.5rem;
            right: 2rem;
            color: var(--text-primary);
            font-size: 2.5rem;
            cursor: pointer;
            transition: color 0.2s;
        }

        .modal-close:hover {
            color: var(--accent-danger);
        }

        .modal-meta {
            position: absolute;
            bottom: 2rem;
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 0.875rem;
            text-align: center;
            background-color: rgba(15, 23, 42, 0.75);
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-section">
            <div class="logo-icon">R</div>
            <h1>Rafiki Vision Hub</h1>
        </div>
        <div class="status-badge">
            <div class="pulse-dot"></div>
            <span id="health-status">CAMÉRA CONNECTÉE</span>
        </div>
    </header>

    <main>
        <!-- Left Panel: Configuration & Live Stream -->
        <div style="display: flex; flex-direction: column; gap: 1.5rem;">
            <!-- Live Stream Panel -->
            <aside class="panel">
                <div class="panel-title">Flux Vidéo en Direct</div>
                <div style="width: 100%; aspect-ratio: 16/9; background-color: #000; border-radius: 0.375rem; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative;">
                    <img id="live-stream-img" src="" alt="Flux vidéo indisponible ou arrêté" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
                <button class="btn-primary" id="btn-toggle-stream" style="width: 100%; margin-top: 0.5rem;">
                    ⏸️ Arrêter le flux
                </button>
            </aside>

            <!-- Configuration Panel -->
            <aside class="panel">
                <div class="panel-title">Contrôle & Configuration</div>
                
                <div class="form-group">
                    <label for="input-api-key">Clé d'API (Optionnel)</label>
                    <input type="password" id="input-api-key" placeholder="Entrez la clé X-API-Key si configurée">
                </div>

                <div class="form-group">
                    <label for="select-width">Résolution Largeur</label>
                    <select id="select-width">
                        <option value="640">640 px</option>
                        <option value="1280" selected>1280 px</option>
                        <option value="1920">1920 px</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="select-height">Résolution Hauteur</label>
                    <select id="select-height">
                        <option value="480">480 px</option>
                        <option value="720" selected>720 px</option>
                        <option value="1080">1080 px</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="select-rotation">Rotation</label>
                    <select id="select-rotation">
                        <option value="0" selected>Aucune</option>
                        <option value="90">90°</option>
                        <option value="180">180°</option>
                        <option value="270">270°</option>
                    </select>
                </div>

                <div class="form-group">
                    <label class="checkbox-group">
                        <input type="checkbox" id="check-flip-h">
                        Flip Horizontal
                    </label>
                </div>

                <div class="form-group">
                    <label class="checkbox-group">
                        <input type="checkbox" id="check-flip-v">
                        Flip Vertical
                    </label>
                </div>

                <button class="btn-primary" id="btn-save-config" style="margin-top: 1rem;">
                    Mettre à jour la caméra
                </button>
            </aside>
        </div>

        <!-- Right Panel: Photos Gallery -->
        <section class="gallery-container">
            <div class="gallery-header">
                <h2>Photos Capturées</h2>
                <div class="gallery-actions">
                    <button class="btn-secondary" id="btn-refresh">🔄 Rafraîchir</button>
                    <button class="btn-danger" id="btn-clear-all">🗑️ Tout Supprimer</button>
                    <button class="btn-primary" id="btn-capture">📸 Prendre une Photo</button>
                </div>
            </div>

            <div class="photos-grid" id="photos-grid">
                <!-- Dynamic Content -->
            </div>
        </section>
    </main>

    <!-- Modal for full screen view -->
    <div class="modal" id="modal-viewer">
        <span class="modal-close" id="modal-close">&times;</span>
        <div class="modal-content">
            <img id="modal-img" src="" alt="Agrandissement">
        </div>
        <div class="modal-meta" id="modal-meta"></div>
    </div>

    <script>
        const grid = document.getElementById('photos-grid');
        const btnRefresh = document.getElementById('btn-refresh');
        const btnClearAll = document.getElementById('btn-clear-all');
        const btnCapture = document.getElementById('btn-capture');
        const btnSaveConfig = document.getElementById('btn-save-config');
        const inputApiKey = document.getElementById('input-api-key');

        const selectWidth = document.getElementById('select-width');
        const selectHeight = document.getElementById('select-height');
        const selectRotation = document.getElementById('select-rotation');
        const checkFlipH = document.getElementById('check-flip-h');
        const checkFlipV = document.getElementById('check-flip-v');

        const modalViewer = document.getElementById('modal-viewer');
        const modalImg = document.getElementById('modal-img');
        const modalClose = document.getElementById('modal-close');
        const modalMeta = document.getElementById('modal-meta');

        // Live stream controls
        const liveStreamImg = document.getElementById('live-stream-img');
        const btnToggleStream = document.getElementById('btn-toggle-stream');
        let streamActive = true;

        // Load stored key
        if (localStorage.getItem('vision_api_key')) {
            inputApiKey.value = localStorage.getItem('vision_api_key');
        }

        function getApiKey() {
            return inputApiKey.value.trim();
        }

        function getHeaders() {
            const key = getApiKey();
            return key ? { 'X-API-Key': key } : {};
        }

        function updateStream() {
            if (!streamActive) {
                liveStreamImg.src = '';
                btnToggleStream.textContent = '▶️ Démarrer le flux';
                btnToggleStream.className = 'btn-primary';
                return;
            }
            btnToggleStream.textContent = '⏸️ Arrêter le flux';
            btnToggleStream.className = 'btn-danger';
            const queryParams = new URLSearchParams();
            const key = getApiKey();
            if (key) queryParams.append('api_key', key);
            queryParams.append('_t', new Date().getTime());
            liveStreamImg.src = `/stream?${queryParams.toString()}`;
        }

        inputApiKey.addEventListener('change', () => {
            localStorage.setItem('vision_api_key', inputApiKey.value);
            updateStream();
        });

        btnToggleStream.addEventListener('click', () => {
            streamActive = !streamActive;
            updateStream();
        });

        async function loadPhotos() {
            try {
                const res = await fetch('/api/photos', { headers: getHeaders() });
                if (!res.ok) throw new Error('Erreur lors du chargement des photos');
                const photos = await res.json();
                
                if (photos.length === 0) {
                    grid.innerHTML = `
                        <div class="empty-state">
                            <span style="font-size: 3rem;">📸</span>
                            <p>Aucune photo n'a été prise pour le moment.</p>
                            <p style="font-size: 0.85rem; color: var(--text-secondary);">Les photos prises via l'API par l'orchestrateur ou manuellement s'afficheront ici.</p>
                        </div>
                    `;
                    return;
                }

                grid.innerHTML = photos.map(photo => `
                    <div class="photo-card">
                        <div class="photo-wrapper" onclick="viewPhoto('${photo.url}', '${photo.filename}')">
                            <img src="${photo.url}" alt="${photo.filename}" loading="lazy">
                        </div>
                        <div class="photo-info">
                            <div class="photo-title">${photo.filename}</div>
                            <div class="photo-meta">
                                <span>${photo.timestamp}</span>
                                <span>${photo.size_kb} Ko</span>
                            </div>
                        </div>
                        <div class="photo-actions">
                            <button class="btn-icon-danger" onclick="deletePhoto('${photo.filename}')" title="Supprimer la photo">
                                🗑️ Supprimer
                            </button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                grid.innerHTML = `<div class="empty-state" style="color: var(--accent-danger); border-color: var(--accent-danger);">${err.message}</div>`;
            }
        }

        async function capturePhoto() {
            btnCapture.disabled = true;
            btnCapture.textContent = 'En cours...';
            
            const w = selectWidth.value;
            const h = selectHeight.value;
            const rot = selectRotation.value;
            const fh = checkFlipH.checked;
            const fv = checkFlipV.checked;
            
            const queryParams = new URLSearchParams({
                width: w,
                height: h,
                rotate: rot,
                flip_h: fh,
                flip_v: fv
            });

            const key = getApiKey();
            if (key) queryParams.append('api_key', key);

            try {
                const res = await fetch(`/capture?${queryParams.toString()}`, { headers: getHeaders() });
                if (!res.ok) throw new Error('La capture a échoué');
                await loadPhotos();
            } catch (err) {
                alert('Erreur lors de la capture : ' + err.message);
            } finally {
                btnCapture.disabled = false;
                btnCapture.textContent = '📸 Prendre une Photo';
            }
        }

        async function deletePhoto(filename) {
            if (!confirm('Supprimer cette photo ?')) return;
            try {
                const res = await fetch(`/api/photos/${filename}`, {
                    method: 'DELETE',
                    headers: getHeaders()
                });
                if (!res.ok) throw new Error('Suppression impossible');
                await loadPhotos();
            } catch (err) {
                alert(err.message);
            }
        }

        async function clearAllPhotos() {
            if (!confirm('Voulez-vous supprimer TOUTES les photos ? Cette action est irréversible.')) return;
            try {
                const res = await fetch('/api/photos', {
                    method: 'DELETE',
                    headers: getHeaders()
                });
                if (!res.ok) throw new Error('Action impossible');
                await loadPhotos();
            } catch (err) {
                alert(err.message);
            }
        }

        async function updateConfig() {
            btnSaveConfig.disabled = true;
            btnSaveConfig.textContent = 'Mise à jour...';
            
            const payload = {
                width: parseInt(selectWidth.value),
                height: parseInt(selectHeight.value),
                rotation: parseInt(selectRotation.value),
                flip_horizontal: checkFlipH.checked,
                flip_vertical: checkFlipV.checked
            };

            try {
                const res = await fetch('/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...getHeaders()
                    },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error('Mise à jour de la configuration échouée');
                alert('Configuration mise à jour avec succès !');
                if (streamActive) {
                    updateStream();
                }
            } catch (err) {
                alert(err.message);
            } finally {
                btnSaveConfig.disabled = false;
                btnSaveConfig.textContent = 'Mettre à jour la caméra';
            }
        }

        function viewPhoto(url, filename) {
            modalImg.src = url;
            modalMeta.textContent = filename;
            modalViewer.style.display = 'flex';
        }

        modalClose.addEventListener('click', () => {
            modalViewer.style.display = 'none';
        });

        modalViewer.addEventListener('click', (e) => {
            if (e.target === modalViewer) {
                modalViewer.style.display = 'none';
            }
        });

        // Initialize
        btnRefresh.addEventListener('click', loadPhotos);
        btnClearAll.addEventListener('click', clearAllPhotos);
        btnCapture.addEventListener('click', capturePhoto);
        btnSaveConfig.addEventListener('click', updateConfig);

        // Fetch initially & start stream
        loadPhotos();
        updateStream();
    </script>
</body>
</html>
"""

def set_global_camera(cam: BaseCamera):
    global _camera_instance
    _camera_instance = cam


def get_camera() -> BaseCamera:
    if _camera_instance is None or not _camera_instance.is_active:
        raise HTTPException(status_code=503, detail="Camera service is not active or available.")
    return _camera_instance


def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None)
):
    """Security check if API key is enabled in settings."""
    key = x_api_key or api_key
    if settings.API_KEY and key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


class ConfigUpdateModel(BaseModel):
    width: Optional[int] = Field(None, ge=160, le=4096)
    height: Optional[int] = Field(None, ge=120, le=2160)
    quality: Optional[int] = Field(None, ge=1, le=100)
    flip_horizontal: Optional[bool] = None
    flip_vertical: Optional[bool] = None
    rotation: Optional[int] = Field(None, description="0, 90, 180, or 270 degrees")


@router.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the main control and validation dashboard for the vision service."""
    return HTMLResponse(content=DASHBOARD_HTML)


@router.get("/health", dependencies=[Depends(verify_api_key)])
def get_health(cam: BaseCamera = Depends(get_camera)):
    """Health check endpoint returning hardware status and camera configuration."""
    return {
        "status": "online",
        "device_name": settings.DEVICE_NAME,
        "camera_type": cam.get_camera_type(),
        "is_active": cam.is_active,
        "settings": {
            "default_width": settings.DEFAULT_WIDTH,
            "default_height": settings.DEFAULT_HEIGHT,
            "default_quality": settings.DEFAULT_QUALITY,
            "format": settings.IMAGE_FORMAT,
            "flip_h": settings.FLIP_HORIZONTAL,
            "flip_v": settings.FLIP_VERTICAL,
            "rotation": settings.ROTATION,
        }
    }


@router.get("/capture", dependencies=[Depends(verify_api_key)])
def capture_image_binary(
    width: Optional[int] = Query(None, ge=160, le=4096),
    height: Optional[int] = Query(None, ge=120, le=2160),
    quality: Optional[int] = Query(None, ge=1, le=100),
    img_format: Optional[Literal["jpeg", "png"]] = Query(None, alias="format"),
    flip_h: Optional[bool] = Query(None),
    flip_v: Optional[bool] = Query(None),
    rotate: Optional[int] = Query(None),
    cam: BaseCamera = Depends(get_camera)
):
    """
    Captures a frame and returns raw binary image (image/jpeg or image/png).
    """
    w = width or settings.DEFAULT_WIDTH
    h = height or settings.DEFAULT_HEIGHT
    q = quality or settings.DEFAULT_QUALITY
    fmt = img_format or settings.IMAGE_FORMAT
    fh = flip_h if flip_h is not None else settings.FLIP_HORIZONTAL
    fv = flip_v if flip_v is not None else settings.FLIP_VERTICAL
    rot = rotate if rotate is not None else settings.ROTATION

    frame_data = cam.capture_frame_data(
        target_width=w,
        target_height=h,
        quality=q,
        img_format=fmt,
        flip_h=fh,
        flip_v=fv,
        rotation=rot
    )

    save_photo_to_disk(frame_data.raw_bytes)

    return Response(
        content=frame_data.raw_bytes,
        media_type=frame_data.mime_type,
        headers={
            "X-Timestamp": frame_data.timestamp,
            "X-Width": str(frame_data.width),
            "X-Height": str(frame_data.height),
            "X-Camera-Type": frame_data.camera_type,
            "X-Device-Name": frame_data.device_name,
        }
    )


@router.get("/capture/json", dependencies=[Depends(verify_api_key)])
def capture_image_json(
    width: Optional[int] = Query(None, ge=160, le=4096),
    height: Optional[int] = Query(None, ge=120, le=2160),
    quality: Optional[int] = Query(None, ge=1, le=100),
    img_format: Optional[Literal["jpeg", "png"]] = Query(None, alias="format"),
    flip_h: Optional[bool] = Query(None),
    flip_v: Optional[bool] = Query(None),
    rotate: Optional[int] = Query(None),
    cam: BaseCamera = Depends(get_camera)
):
    """
    Captures a frame and returns JSON formatted with Base64 payload and Data URI.
    Tailor-made for direct injection into Vision LLM prompts (OpenAI, Claude, Ollama, Gemini).
    """
    w = width or settings.DEFAULT_WIDTH
    h = height or settings.DEFAULT_HEIGHT
    q = quality or settings.DEFAULT_QUALITY
    fmt = img_format or settings.IMAGE_FORMAT
    fh = flip_h if flip_h is not None else settings.FLIP_HORIZONTAL
    fv = flip_v if flip_v is not None else settings.FLIP_VERTICAL
    rot = rotate if rotate is not None else settings.ROTATION

    frame_data = cam.capture_frame_data(
        target_width=w,
        target_height=h,
        quality=q,
        img_format=fmt,
        flip_h=fh,
        flip_v=fv,
        rotation=rot
    )

    save_photo_to_disk(frame_data.raw_bytes)

    return frame_data.to_llm_payload()


@router.get("/stream", dependencies=[Depends(verify_api_key)])
def mjpeg_video_stream(
    fps: int = Query(15, ge=1, le=60),
    quality: int = Query(70, ge=1, le=100),
    flip_h: Optional[bool] = Query(None),
    flip_v: Optional[bool] = Query(None),
    rotate: Optional[int] = Query(None),
    cam: BaseCamera = Depends(get_camera)
):
    """
    Returns an MJPEG multipart video stream for real-time preview in web browsers.
    """
    fh = flip_h if flip_h is not None else settings.FLIP_HORIZONTAL
    fv = flip_v if flip_v is not None else settings.FLIP_VERTICAL
    rot = rotate if rotate is not None else settings.ROTATION

    generator = cam.generate_mjpeg_stream(
        fps=fps,
        quality=quality,
        flip_h=fh,
        flip_v=fv,
        rotation=rot
    )

    return StreamingResponse(
        generator,
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/config", dependencies=[Depends(verify_api_key)])
def update_configuration(config: ConfigUpdateModel):
    """Dynamically updates default settings without restarting the service."""
    if config.width is not None:
        settings.DEFAULT_WIDTH = config.width
    if config.height is not None:
        settings.DEFAULT_HEIGHT = config.height
    if config.quality is not None:
        settings.DEFAULT_QUALITY = config.quality
    if config.flip_horizontal is not None:
        settings.FLIP_HORIZONTAL = config.flip_horizontal
    if config.flip_vertical is not None:
        settings.FLIP_VERTICAL = config.flip_vertical
    if config.rotation is not None:
        settings.ROTATION = config.rotation

    return {
        "status": "updated",
        "current_settings": {
            "width": settings.DEFAULT_WIDTH,
            "height": settings.DEFAULT_HEIGHT,
            "quality": settings.DEFAULT_QUALITY,
            "flip_h": settings.FLIP_HORIZONTAL,
            "flip_v": settings.FLIP_VERTICAL,
            "rotation": settings.ROTATION,
        }
    }


# Photo Gallery APIs
@router.get("/api/photos")
def get_photos():
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    files = glob.glob(os.path.join(PHOTOS_DIR, "photo_*.jpg"))
    # Sort by modification time descending
    files.sort(key=os.path.getmtime, reverse=True)
    
    photos_list = []
    for f in files:
        filename = os.path.basename(f)
        try:
            mtime = os.path.getmtime(f)
            dt = datetime.fromtimestamp(mtime)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp_str = "Inconnue"
            
        try:
            sz = os.path.getsize(f)
            size_kb = round(sz / 1024.0, 1)
        except Exception:
            size_kb = 0.0
            
        photos_list.append({
            "filename": filename,
            "timestamp": timestamp_str,
            "size_kb": size_kb,
            "url": f"/api/photos/{filename}"
        })
    return photos_list


@router.get("/api/photos/{filename}")
def get_photo_file(filename: str):
    filepath = os.path.join(PHOTOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Photo non trouvée")
    return FileResponse(filepath, media_type="image/jpeg")


@router.delete("/api/photos/{filename}")
def delete_photo_file(filename: str):
    filepath = os.path.join(PHOTOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Photo non trouvée")
    try:
        os.remove(filepath)
        return {"status": "success", "message": f"Photo {filename} supprimée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/photos")
def delete_all_photos():
    try:
        if os.path.exists(PHOTOS_DIR):
            for f in glob.glob(os.path.join(PHOTOS_DIR, "photo_*.jpg")):
                os.remove(f)
        return {"status": "success", "message": "Toutes les photos ont été supprimées"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
