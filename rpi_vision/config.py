"""
Configuration management using pydantic-settings.
"""
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Camera settings
    CAMERA_TYPE: Literal["auto", "opencv", "picamera2", "mock"] = "auto"
    CAMERA_INDEX: str = "0"  # Can be integer "0" for USB or RTSP url "rtsp://..."
    DEFAULT_WIDTH: int = 1280
    DEFAULT_HEIGHT: int = 720
    DEFAULT_QUALITY: int = 85  # JPEG quality (1-100)
    IMAGE_FORMAT: Literal["jpeg", "png"] = "jpeg"
    FLIP_HORIZONTAL: bool = False
    FLIP_VERTICAL: bool = False
    ROTATION: int = 0  # 0, 90, 180, 270 degrees

    # Server & Security settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_KEY: Optional[str] = None  # If set, X-API-Key header will be required
    DEVICE_NAME: str = "RaspberryPi-Vision-01"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def parsed_camera_index(self) -> int | str:
        """Parses CAMERA_INDEX as int if numeric (USB dev), otherwise string (RTSP/file)."""
        if self.CAMERA_INDEX.isdigit():
            return int(self.CAMERA_INDEX)
        return self.CAMERA_INDEX


settings = Settings()
