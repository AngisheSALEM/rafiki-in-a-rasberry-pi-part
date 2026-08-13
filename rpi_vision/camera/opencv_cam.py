"""
OpenCV Camera Implementation (USB Webcams, V4L2 devices, RTSP streams).
"""
import cv2
import numpy as np
import threading
import time
from typing import Union
from .base import BaseCamera


class OpenCVCamera(BaseCamera):
    """OpenCV implementation for USB cameras & RTSP streams."""

    def __init__(
        self,
        camera_index: Union[int, str] = 0,
        device_name: str = "USB-Webcam",
        default_width: int = 1280,
        default_height: int = 720
    ):
        super().__init__(device_name=device_name)
        self.camera_index = camera_index
        self.default_width = default_width
        self.default_height = default_height
        self.cap: cv2.VideoCapture = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.is_active and self.cap and self.cap.isOpened():
                return

            if isinstance(self.camera_index, str) and self.camera_index.isdigit():
                idx = int(self.camera_index)
            else:
                idx = self.camera_index

            self.cap = cv2.VideoCapture(idx)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open OpenCV camera with index/url: {self.camera_index}")

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.default_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.default_height)
            self.is_active = True
            time.sleep(0.3)

    def stop(self) -> None:
        with self._lock:
            self.is_active = False
            if self.cap:
                self.cap.release()
                self.cap = None

    def capture_raw_frame(self) -> np.ndarray:
        with self._lock:
            if not self.is_active or self.cap is None or not self.cap.isOpened():
                self.start()

            for _ in range(2):
                ret, frame = self.cap.read()
                if not ret:
                    break

            if not ret or frame is None:
                raise RuntimeError("Failed to read frame from OpenCV camera.")

            return frame

    def get_camera_type(self) -> str:
        return "opencv_v4l2"
