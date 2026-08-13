"""
Camera abstraction package.
"""
from .base import BaseCamera, FrameData
from .factory import create_camera

__all__ = ["BaseCamera", "FrameData", "create_camera"]
