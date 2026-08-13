"""
Raspberry Pi Official Camera Module implementation using Picamera2 / libcamera.
"""
import cv2
import numpy as np
import threading
import time
from typing import Optional
from .base import BaseCamera

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    Picamera2 = None
    PICAMERA2_AVAILABLE = False


class PiCamera2Adapter(BaseCamera):
    """Adapter for official Raspberry Pi CSI Camera Modules via Picamera2."""

    def __init__(
        self,
        device_name: str = "RPi-CSI-Camera",
        default_width: int = 1280,
        default_height: int = 720
    ):
        super().__init__(device_name=device_name)
        if not PICAMERA2_AVAILABLE:
            raise ImportError(
                "picamera2 module is not installed on this system. "
                "Install it using 'sudo apt install python3-picamera2' on Raspberry Pi OS."
            )
        self.default_width = default_width
        self.default_height = default_height
        self.picam2: Optional[Picamera2] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.is_active and self.picam2:
                return

            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"size": (self.default_width, self.default_height), "format": "RGB888"}
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.is_active = True
            time.sleep(0.5)

    def stop(self) -> None:
        with self._lock:
            self.is_active = False
            if self.picam2:
                try:
                    self.picam2.stop()
                    self.picam2.close()
                except Exception:
                    pass
                self.picam2 = None

    def capture_raw_frame(self) -> np.ndarray:
        with self._lock:
            if not self.is_active or self.picam2 is None:
                self.start()

            rgb_array = self.picam2.capture_array()
            bgr_frame = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
            return bgr_frame

    def get_camera_type(self) -> str:
        return "picamera2_libcamera"
