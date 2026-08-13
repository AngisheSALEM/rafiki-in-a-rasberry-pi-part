"""
Automatic Vision Frame Pusher Service for Raspberry Pi.
Runs on boot via systemd. Automatically connects to Orchestrator Server (10.20.20.224:7860),
registers the camera microservice, and pushes frames continuously without human intervention.
"""
from __future__ import annotations

import argparse
import logging
import time
from typing import Any, Dict, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rpi_vision.pusher")


def push_single_frame(
    server_url: str,
    local_vision_url: str,
    width: int = 1280,
    height: int = 720,
    quality: int = 85,
    timeout: float = 5.0,
) -> bool:
    """Helper to capture one frame from local OV5647 camera service and push it to server."""
    # 1. Capture frame
    cap_resp = requests.get(
        f"{local_vision_url}/capture/json",
        params={"width": width, "height": height, "quality": quality},
        timeout=timeout,
    )
    cap_resp.raise_for_status()
    payload = cap_resp.json()

    raw_uri = payload.get("data_uri", "")
    image_b64 = raw_uri.split(",")[-1] if "," in raw_uri else payload.get("image_base64", "")
    meta = payload.get("metadata", {})

    # 2. Push frame
    upload_resp = requests.post(
        f"{server_url}/api/vision/upload",
        json={
            "image_base64": image_b64,
            "width": meta.get("width", width),
            "height": meta.get("height", height),
            "camera_type": meta.get("camera_type", "ov5647"),
        },
        timeout=timeout,
    )
    upload_resp.raise_for_status()
    return True


def register_camera_service(server_url: str, local_vision_url: str, timeout: float = 3.0) -> bool:
    """Helper to register local camera endpoint with the server."""
    resp = requests.post(
        f"{server_url}/api/vision/register",
        json={"vision_url": local_vision_url},
        timeout=timeout,
    )
    return resp.status_code == 200


def run_pusher(
    *,
    server_url: str = "http://10.20.20.224:7860",
    local_vision_url: str = "http://localhost:8000",
    push_interval: float = 2.0,
    retry_interval: float = 5.0,
    max_loops: Optional[int] = None,
) -> None:
    server_url = server_url.rstrip("/")
    local_vision_url = local_vision_url.rstrip("/")

    logger.info("Starting Vision Frame Pusher Daemon...")
    logger.info(f" Server URL:        {server_url}")
    logger.info(f" Local Vision URL:  {local_vision_url}")
    logger.info(f" Push Interval:     {push_interval}s")

    registered = False
    loop_count = 0

    while True:
        if max_loops is not None and loop_count >= max_loops:
            break
        loop_count += 1

        # 1. Register with server if needed
        if not registered:
            try:
                if register_camera_service(server_url, local_vision_url):
                    logger.info(f"Registered camera with orchestrator server {server_url}")
                    registered = True
                else:
                    registered = False
            except requests.RequestException as exc:
                logger.warning(f"Waiting for Orchestrator Server at {server_url}... ({exc})")
                registered = False
                time.sleep(retry_interval)
                continue

        # 2. Push frame
        try:
            push_single_frame(server_url, local_vision_url)
            logger.debug("Pushed camera frame to server successfully.")
        except requests.RequestException as exc:
            logger.warning(f"Camera push failed ({exc}), retrying...")
            registered = False
            time.sleep(retry_interval)
            continue

        time.sleep(push_interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Raspberry Pi Vision Automatic Pusher Daemon")
    parser.add_argument("--server-url", default="http://10.20.20.224:7860", help="Orchestrator server URL")
    parser.add_argument("--local-vision-url", default="http://localhost:8000", help="Local camera microservice URL")
    parser.add_argument("--push-interval", type=float, default=2.0, help="Interval between frame pushes in seconds")
    parser.add_argument("--retry-interval", type=float, default=5.0, help="Retry interval on connection loss")
    args = parser.parse_args()

    try:
        run_pusher(
            server_url=args.server_url,
            local_vision_url=args.local_vision_url,
            push_interval=args.push_interval,
            retry_interval=args.retry_interval,
        )
        return 0
    except KeyboardInterrupt:
        logger.info("Vision Pusher stopped by user.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
