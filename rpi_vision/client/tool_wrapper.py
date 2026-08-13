"""
Client Tool Wrapper for external Orchestrators and LLM Agents.
Allows any external agent framework to invoke the Raspberry Pi camera service easily.
"""
import requests
from typing import Optional, Dict, Any


class RpiVisionClient:
    """Client helper class to communicate with the Raspberry Pi Vision Service."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key

    def health(self) -> Dict[str, Any]:
        """Check if the Pi Vision microservice is online."""
        resp = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=5.0)
        resp.raise_for_status()
        return resp.json()

    def capture_image_json(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: Optional[int] = None,
        img_format: str = "jpeg",
        flip_h: Optional[bool] = None,
        flip_v: Optional[bool] = None,
        rotate: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Captures a fresh image from the Raspberry Pi camera and returns a JSON dict
        containing the Base64 image payload ready for Vision LLMs.
        """
        params = {}
        if width:
            params["width"] = width
        if height:
            params["height"] = height
        if quality:
            params["quality"] = quality
        if img_format:
            params["format"] = img_format
        if flip_h is not None:
            params["flip_h"] = flip_h
        if flip_v is not None:
            params["flip_v"] = flip_v
        if rotate is not None:
            params["rotate"] = rotate

        resp = requests.get(
            f"{self.base_url}/capture/json",
            headers=self.headers,
            params=params,
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()

    def capture_image_bytes(
        self,
        save_path: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: Optional[int] = None
    ) -> bytes:
        """Captures raw image bytes and optionally saves to file."""
        params = {}
        if width:
            params["width"] = width
        if height:
            params["height"] = height
        if quality:
            params["quality"] = quality

        resp = requests.get(
            f"{self.base_url}/capture",
            headers=self.headers,
            params=params,
            timeout=10.0
        )
        resp.raise_for_status()
        image_bytes = resp.content

        if save_path:
            with open(save_path, "wb") as f:
                f.write(image_bytes)

        return image_bytes


def get_vision_tool_definition() -> Dict[str, Any]:
    """
    Returns OpenAI / Universal Tool Definition schema for function calling orchestrators.
    """
    return {
        "type": "function",
        "function": {
            "name": "rpi_capture_camera_image",
            "description": "Prend une photo avec la caméra du Raspberry Pi et retourne l'image en base64 pour analyse visuelle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Raison ou contexte de la prise de photo (ex: 'Vérifier la présence d'un objet sur la table')"
                    },
                    "quality": {
                        "type": "integer",
                        "description": "Qualité d'image JPEG (1 à 100). Défaut: 85",
                        "default": 85
                    }
                },
                "required": ["reason"]
            }
        }
    }
