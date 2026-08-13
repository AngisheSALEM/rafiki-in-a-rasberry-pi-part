from __future__ import annotations

import shutil
import subprocess
from typing import Callable


class TextToSpeechError(RuntimeError):
    """Raised when Rafiki cannot speak through the configured TTS engine."""


class EspeakTTS:
    def __init__(
        self,
        executable: str = "espeak-ng",
        voice: str = "fr-fr",
        speed: int = 155,
        pitch: int = 45,
        enabled: bool = True,
    ) -> None:
        self.executable = executable
        self.voice = voice
        self.speed = speed
        self.pitch = pitch
        self.enabled = enabled

    def is_available(self) -> bool:
        return shutil.which(self.executable) is not None

    def speak(
        self,
        text: str,
        on_playback_start: Callable[[], None] | None = None,
        on_playback_end: Callable[[], None] | None = None,
    ) -> None:
        content = text.strip()
        if not self.enabled or not content:
            return

        if not self.is_available():
            raise TextToSpeechError(f"{self.executable} is not installed")

        command = [
            self.executable,
            "-v",
            self.voice,
            "-s",
            str(self.speed),
            "-p",
            str(self.pitch),
            content,
        ]

        playback_started = False
        try:
            if on_playback_start:
                on_playback_start()
            playback_started = True
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            raise TextToSpeechError(f"TTS command failed: {exc}") from exc
        finally:
            if playback_started and on_playback_end:
                on_playback_end()


def prepare_spoken_text(text: str, max_words: int | None = None) -> str:
    normalized = " ".join(text.strip().split())
    replacements = {
        "LLM": "cerveau",
        "JSON": "données",
        "STT": "écoute",
        "TTS": "voix",
        "Rafiki !": "Rafiki.",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    words = normalized.split()
    if max_words is not None and len(words) > max_words:
        normalized = " ".join(words[:max_words]).rstrip(" ,;:")
        if not normalized.endswith((".", "!", "?")):
            normalized += "."

    if normalized and normalized[-1] not in ".!?":
        normalized += "."

    return normalized
