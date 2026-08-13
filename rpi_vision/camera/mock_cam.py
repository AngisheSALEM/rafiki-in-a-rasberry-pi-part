"""
Mock Camera implementation for testing on environments without physical hardware.
"""
import cv2
import numpy as np
import math
import time
from datetime import datetime, timezone
from .base import BaseCamera


class MockCamera(BaseCamera):
    """Synthetic test camera generator."""

    def __init__(
        self,
        device_name: str = "Mock-RPi-Cam",
        default_width: int = 1280,
        default_height: int = 720
    ):
        super().__init__(device_name=device_name)
        self.width = default_width
        self.height = default_height
        self.frame_count = 0

    def start(self) -> None:
        self.is_active = True

    def stop(self) -> None:
        self.is_active = False

    def capture_raw_frame(self) -> np.ndarray:
        self.frame_count += 1
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        for y in range(self.height):
            img[y, :, 0] = int(40 + (y / self.height) * 40)
            img[y, :, 1] = int(30 + (y / self.height) * 30)
            img[y, :, 2] = int(20 + (y / self.height) * 20)

        bar_height = int(self.height * 0.15)
        colors = [
            (255, 255, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0),
            (255, 0, 255), (0, 0, 255), (255, 0, 0), (0, 0, 0)
        ]
        bar_width = self.width // len(colors)
        for i, color in enumerate(colors):
            img[0:bar_height, i * bar_width:(i + 1) * bar_width] = color

        t = time.time()
        cx = int((self.width / 2) + math.sin(t * 2) * (self.width / 3))
        cy = int((self.height / 2) + math.cos(t * 3) * (self.height / 4))
        cv2.circle(img, (cx, cy), 40, (0, 200, 255), -1)
        cv2.circle(img, (cx, cy), 42, (255, 255, 255), 2)

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        cv2.putText(img, "RASPBERRY PI VISION SERVICE (SIMULATOR)", (40, bar_height + 60), font, 0.9, (0, 255, 0), 2)
        cv2.putText(img, f"Device: {self.device_name}", (40, bar_height + 100), font, 0.7, (255, 255, 255), 1)
        cv2.putText(img, f"Timestamp: {now_str}", (40, bar_height + 140), font, 0.7, (255, 255, 255), 1)
        cv2.putText(img, f"Resolution: {self.width}x{self.height} | Frame #{self.frame_count}", (40, bar_height + 180), font, 0.7, (200, 200, 200), 1)
        cv2.putText(img, "Status: Ready for LLM Orchestrator Vision Tool", (40, bar_height + 230), font, 0.8, (0, 255, 255), 2)

        return img

    def get_camera_type(self) -> str:
        return "mock_synthetic"
