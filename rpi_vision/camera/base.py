"""
Base Abstract Camera Interface and Frame metadata structures.
"""
import base64
import cv2
import numpy as np
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Generator, Tuple


@dataclass
class FrameData:
    raw_bytes: bytes
    base64_str: str
    mime_type: str
    width: int
    height: int
    timestamp: str
    camera_type: str
    device_name: str

    def to_llm_payload(self) -> dict:
        """
        Formats frame data ready to be inserted directly into Vision LLM API payloads
        (e.g., OpenAI GPT-4o, Claude 3.5 Sonnet, Ollama, Gemini).
        """
        data_uri = f"data:{self.mime_type};base64,{self.base64_str}"
        return {
            "mime_type": self.mime_type,
            "data_uri": data_uri,
            "base64": self.base64_str,
            "metadata": {
                "timestamp": self.timestamp,
                "width": self.width,
                "height": self.height,
                "camera_type": self.camera_type,
                "device_name": self.device_name,
            }
        }


class BaseCamera(ABC):
    """Abstract Base Camera Class."""

    def __init__(self, device_name: str = "RaspberryPi-Cam"):
        self.device_name = device_name
        self.is_active = False

    @abstractmethod
    def start(self) -> None:
        """Initialize and open camera connection."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Close camera connection and release hardware resources."""
        pass

    @abstractmethod
    def capture_raw_frame(self) -> np.ndarray:
        """Returns raw BGR numpy array from hardware."""
        pass

    @abstractmethod
    def get_camera_type(self) -> str:
        """Returns string identifier of camera implementation."""
        pass

    def apply_transformations(
        self,
        frame: np.ndarray,
        flip_h: bool = False,
        flip_v: bool = False,
        rotation: int = 0,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None
    ) -> np.ndarray:
        """Applies horizontal/vertical flipping, rotation, and resizing."""
        # Flip
        if flip_h and flip_v:
            frame = cv2.flip(frame, -1)
        elif flip_h:
            frame = cv2.flip(frame, 1)
        elif flip_v:
            frame = cv2.flip(frame, 0)

        # Rotate
        if rotation == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Resize if dimensions specified
        if target_width and target_height:
            h, w = frame.shape[:2]
            if w != target_width or h != target_height:
                frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)

        return frame

    def capture_frame_data(
        self,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        quality: int = 85,
        img_format: str = "jpeg",
        flip_h: bool = False,
        flip_v: bool = False,
        rotation: int = 0
    ) -> FrameData:
        """Captures a frame and encodes it to raw bytes and Base64 string."""
        raw_frame = self.capture_raw_frame()
        processed_frame = self.apply_transformations(
            raw_frame,
            flip_h=flip_h,
            flip_v=flip_v,
            rotation=rotation,
            target_width=target_width,
            target_height=target_height
        )

        height, width = processed_frame.shape[:2]
        ext = ".jpg" if img_format.lower() in ["jpeg", "jpg"] else ".png"
        mime_type = "image/jpeg" if ext == ".jpg" else "image/png"

        encode_params = []
        if ext == ".jpg":
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(1, min(100, quality))]

        success, buffer = cv2.imencode(ext, processed_frame, encode_params)
        if not success:
            raise RuntimeError("Failed to encode camera frame to image buffer.")

        raw_bytes = buffer.tobytes()
        base64_str = base64.b64encode(raw_bytes).decode("utf-8")
        iso_timestamp = datetime.now(timezone.utc).isoformat()

        return FrameData(
            raw_bytes=raw_bytes,
            base64_str=base64_str,
            mime_type=mime_type,
            width=width,
            height=height,
            timestamp=iso_timestamp,
            camera_type=self.get_camera_type(),
            device_name=self.device_name
        )

    def generate_mjpeg_stream(
        self,
        fps: int = 15,
        quality: int = 70,
        flip_h: bool = False,
        flip_v: bool = False,
        rotation: int = 0
    ) -> Generator[bytes, None, None]:
        """Yields multipart MJPEG frame chunks suitable for StreamingResponse."""
        delay = 1.0 / max(1, fps)
        while self.is_active:
            try:
                frame_data = self.capture_frame_data(
                    quality=quality,
                    img_format="jpeg",
                    flip_h=flip_h,
                    flip_v=flip_v,
                    rotation=rotation
                )
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_data.raw_bytes + b'\r\n'
                )
                time.sleep(delay)
            except Exception:
                time.sleep(0.1)
