from __future__ import annotations

import base64
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from collections import deque

import requests
from fastapi import FastAPI, HTTPException, File, UploadFile, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from orchestrator.services.llm_client import RafikiLLMClient, RafikiDecision
from orchestrator.services.fallback_client import FallbackRafikiClient
from body.controller import build_body_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rafiki.orchestrator.server")


app = FastAPI(
    title="Rafiki Orchestrator & Hardware Bridge Server",
    description=(
        "Central API server running on PC (10.20.20.224:7860) bridging "
        "Raspberry Pi Vision Service (camgo / hardware camera OV5647) and "
        "Raspberry Pi Body Controller (Arduino Mega serial sync / body_pull_client.py)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# In-Memory State for Hardware Bridge
# -----------------------------------------------------------------------------

class BridgeState:
    def __init__(self) -> None:
        # Body queue: pending commands for body_pull_client.py
        self.body_queue: deque[Dict[str, Any]] = deque()
        self.latest_body_status: Dict[str, Any] = {
            "connected": False,
            "last_updated": 0,
            "body_port": None,
            "last_command_id": None,
            "last_action": None,
            "serial_commands": [],
            "error": None,
        }

        # Vision state: registered camera microservice & pushed frames
        self.vision_url: str = "http://127.0.0.1:8000"
        self.latest_vision_frame: Optional[Dict[str, Any]] = None
        self.latest_vision_status: Dict[str, Any] = {
            "registered_url": "http://127.0.0.1:8000",
            "connected": False,
            "last_capture_timestamp": None,
            "last_error": None,
        }

        # LLM Clients
        self.llm_client = RafikiLLMClient()
        self.fallback_client = FallbackRafikiClient()


state = BridgeState()


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

class BodyCommandRequest(BaseModel):
    action: str = Field(..., description="Action: set_expression, motor_gesture, screen_text, status_ping")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the command")


class BodyStatusPayload(BaseModel):
    status: Dict[str, Any] = Field(..., description="Status dictionary sent by body_pull_client.py")


class VisionRegisterRequest(BaseModel):
    vision_url: str = Field(..., json_schema_extra={"example": "http://10.20.20.150:8000"}, description="URL of the Raspberry Pi Vision service")


class VisionFrameUpload(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded JPEG image from camera")
    width: Optional[int] = None
    height: Optional[int] = None
    camera_type: Optional[str] = "ov5647"


class OrchestrateRequest(BaseModel):
    user_message: str = Field(..., json_schema_extra={"example": "Bonjour Rafiki, comment vas-tu ?"})
    include_vision: bool = Field(default=False, description="Capture frame from Raspberry Pi before calling LLM")
    language: str = Field(default="fr", description="Language code")



# -----------------------------------------------------------------------------
# Health & Root Routes
# -----------------------------------------------------------------------------

@app.get("/")
def get_root():
    return {
        "service": "Rafiki Orchestrator Bridge Server",
        "host": "10.20.20.224:7860",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def get_health():
    body_online = (time.time() - state.latest_body_status.get("last_updated", 0)) < 15.0
    return {
        "status": "online",
        "timestamp": time.time(),
        "bridge": {
            "body_pull_client_online": body_online,
            "pending_body_commands": len(state.body_queue),
            "vision_url": state.vision_url,
            "has_latest_frame": state.latest_vision_frame is not None,
        },
    }


@app.get("/api/bridge/status")
def get_bridge_status():
    """Overall status of both Body (Arduino) and Vision (Camera) bridge services."""
    now = time.time()
    body_last = state.latest_body_status.get("last_updated", 0)
    body_online = (now - body_last) < 15.0 if body_last > 0 else False

    return {
        "timestamp": now,
        "body": {
            "online": body_online,
            "queue_length": len(state.body_queue),
            "last_status": state.latest_body_status,
        },
        "vision": {
            "registered_url": state.vision_url,
            "latest_frame_time": state.latest_vision_frame.get("timestamp") if state.latest_vision_frame else None,
            "status": state.latest_vision_status,
        },
    }


# -----------------------------------------------------------------------------
# Body / Movement API Routes (Polled by body_pull_client.py on Raspberry Pi)
# -----------------------------------------------------------------------------

@app.get("/api/body/next")
def get_body_next():
    """
    Polled by `body_pull_client.py` on Raspberry Pi.
    Returns the next pending command to transmit to Arduino Mega via serial.
    """
    if not state.body_queue:
        return {"command": None}

    command = state.body_queue.popleft()
    logger.info(f"Dispatching body command to Raspberry Pi: {command}")
    return {"command": command}


@app.post("/api/body/status")
def post_body_status(payload: BodyStatusPayload):
    """
    Called by `body_pull_client.py` to report Raspberry Pi & Arduino status.
    """
    status_data = payload.status
    status_data["last_updated"] = time.time()
    state.latest_body_status.update(status_data)
    logger.debug(f"Received body status update: {status_data}")
    return {"status": "ok", "received_at": status_data["last_updated"]}


@app.get("/api/body/status")
def get_body_status():
    """Returns current status of Raspberry Pi Body Controller."""
    now = time.time()
    last_upd = state.latest_body_status.get("last_updated", 0)
    online = (now - last_upd) < 15.0 if last_upd > 0 else False
    return {
        "online": online,
        "queue_length": len(state.body_queue),
        "status": state.latest_body_status,
    }


@app.post("/api/body/enqueue")
@app.post("/api/body/command")
def enqueue_body_command(req: BodyCommandRequest):
    """
    Enqueue a manual or agent command for the body controller (Arduino).
    """
    command_id = uuid.uuid4().hex[:12]
    cmd = {
        "id": command_id,
        "action": req.action,
        "params": req.params,
        "enqueued_at": time.time(),
    }
    state.body_queue.append(cmd)
    logger.info(f"Enqueued body command [{command_id}]: {req.action} {req.params}")
    return {
        "status": "enqueued",
        "command_id": command_id,
        "queue_length": len(state.body_queue),
    }


# -----------------------------------------------------------------------------
# Vision / Camera API Routes (Connected to camgo / rpi_vision on Raspberry Pi)
# -----------------------------------------------------------------------------

@app.post("/api/vision/register")
def register_vision_service(req: VisionRegisterRequest):
    """
    Register the Raspberry Pi vision microservice URL (e.g., http://10.20.20.150:8000).
    """
    state.vision_url = req.vision_url.rstrip("/")
    state.latest_vision_status["registered_url"] = state.vision_url
    logger.info(f"Registered Raspberry Pi Vision Service at: {state.vision_url}")
    return {"status": "registered", "vision_url": state.vision_url}


@app.post("/api/vision/upload")
def upload_vision_frame(upload: VisionFrameUpload):
    """
    Endpoint for Raspberry Pi (or camgo helper) to push captured image frames directly to server.
    """
    ts = time.time()
    state.latest_vision_frame = {
        "timestamp": ts,
        "image_base64": upload.image_base64,
        "width": upload.width,
        "height": upload.height,
        "camera_type": upload.camera_type or "ov5647",
    }
    state.latest_vision_status["last_capture_timestamp"] = ts
    state.latest_vision_status["connected"] = True
    logger.info(f"Received uploaded vision frame ({upload.width}x{upload.height}) at {ts}")
    return {"status": "received", "timestamp": ts}


@app.post("/api/vision/upload_binary")
async def upload_vision_binary(file: UploadFile = File(...)):
    """
    Upload raw binary JPEG image from Raspberry Pi.
    """
    contents = await file.read()
    b64_str = base64.b64encode(contents).decode("utf-8")
    ts = time.time()
    state.latest_vision_frame = {
        "timestamp": ts,
        "image_base64": b64_str,
        "content_type": file.content_type or "image/jpeg",
        "size_bytes": len(contents),
    }
    state.latest_vision_status["last_capture_timestamp"] = ts
    state.latest_vision_status["connected"] = True
    logger.info(f"Received binary camera upload ({len(contents)} bytes)")
    return {"status": "received", "size_bytes": len(contents), "timestamp": ts}


@app.get("/api/vision/latest")
def get_latest_vision_frame():
    """
    Retrieve the latest camera frame uploaded to the orchestrator server.
    """
    if not state.latest_vision_frame:
        raise HTTPException(status_code=444, detail="No camera frame available yet")
    return state.latest_vision_frame


@app.get("/api/vision/status")
def get_vision_status():
    """Get status of the camera vision bridge."""
    return {
        "vision_url": state.vision_url,
        "has_frame": state.latest_vision_frame is not None,
        "latest_frame_time": state.latest_vision_frame.get("timestamp") if state.latest_vision_frame else None,
        "status": state.latest_vision_status,
    }


@app.api_route("/api/vision/capture", methods=["GET", "POST"])
def trigger_vision_capture(width: int = 1280, height: int = 720, quality: int = 85):
    """
    Triggers an image capture directly from the registered Raspberry Pi Vision microservice.
    """
    target_url = f"{state.vision_url}/capture/json"
    params = {"width": width, "height": height, "quality": quality}
    try:
        resp = requests.get(target_url, params=params, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
        
        # Save to state
        state.latest_vision_frame = {
            "timestamp": time.time(),
            "image_base64": data.get("data_uri", "").split(",")[-1] if "," in data.get("data_uri", "") else data.get("image_base64", ""),
            "metadata": data.get("metadata", {}),
        }
        state.latest_vision_status["connected"] = True
        state.latest_vision_status["last_capture_timestamp"] = state.latest_vision_frame["timestamp"]
        return data
    except Exception as exc:
        state.latest_vision_status["last_error"] = str(exc)
        logger.error(f"Failed to capture frame from Raspberry Pi Vision Service ({target_url}): {exc}")
        
        # Fallback to latest stored frame if present
        if state.latest_vision_frame:
            return {
                "status": "warning",
                "message": f"Could not reach live camera endpoint ({exc}), returning latest cached frame.",
                "cached_frame": state.latest_vision_frame,
            }
        raise HTTPException(status_code=502, detail=f"Cannot reach Raspberry Pi Vision Service at {target_url}: {exc}")


# -----------------------------------------------------------------------------
# Orchestration Engine API Route
# -----------------------------------------------------------------------------

def enqueue_decision_commands(decision: RafikiDecision) -> List[Dict[str, Any]]:
    """Translates a Rafiki LLM Decision into body commands and enqueues them."""
    enqueued = []

    # 1. Expression command
    if decision.emotion:
        cmd_id = uuid.uuid4().hex[:12]
        cmd = {
            "id": cmd_id,
            "action": "set_expression",
            "params": {"emotion": decision.emotion},
            "enqueued_at": time.time(),
        }
        state.body_queue.append(cmd)
        enqueued.append(cmd)

    # 2. Movement command (if not none)
    if decision.movement and decision.movement != "none":
        cmd_id = uuid.uuid4().hex[:12]
        cmd = {
            "id": cmd_id,
            "action": "motor_gesture",
            "params": {"gesture": decision.movement},
            "enqueued_at": time.time(),
        }
        state.body_queue.append(cmd)
        enqueued.append(cmd)

    # 3. Screen text command
    if decision.screen_mode in {"text", "quiz"} and decision.screen_content:
        cmd_id = uuid.uuid4().hex[:12]
        cmd = {
            "id": cmd_id,
            "action": "screen_text",
            "params": {"text": decision.screen_content},
            "enqueued_at": time.time(),
        }
        state.body_queue.append(cmd)
        enqueued.append(cmd)

    return enqueued


@app.post("/api/orchestrate")
@app.post("/api/orchestration/step")
def orchestrate_step(req: OrchestrateRequest):
    """
    Main Orchestration endpoint linking User/Vision input to LLM Decision,
    and automatically bridging decisions to Raspberry Pi Body (Arduino) and Vision.
    """
    logger.info(f"Orchestration request: '{req.user_message}' (include_vision={req.include_vision})")

    vision_analyzed = False
    if req.include_vision:
        try:
            trigger_vision_capture()
            vision_analyzed = True
        except Exception as e:
            logger.warning(f"Could not include live vision frame in orchestration: {e}")

    # Generate decision using LLM or Fallback
    try:
        decision = state.llm_client.generate(user_message=req.user_message, language=req.language)
    except Exception as exc:
        logger.warning(f"Primary LLM client unavailable ({exc}), using Fallback decision engine.")
        decision = state.fallback_client.generate(user_message=req.user_message, language=req.language)

    # Enqueue commands for Raspberry Pi / Arduino Mega synchronization
    enqueued = enqueue_decision_commands(decision)

    return {
        "status": "success",
        "decision": decision.model_dump(),
        "enqueued_body_commands": enqueued,
        "vision_included": vision_analyzed,
        "queue_length": len(state.body_queue),
    }
