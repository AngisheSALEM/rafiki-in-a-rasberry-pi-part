import pytest

from voice.stt import (
    PulseWhisperSpeechToText,
    pcm16_rms,
)

from array import array


def test_pcm16_rms_detects_silence_and_signal() -> None:
    assert pcm16_rms(b"\x00\x00" * 20) == 0.0
    signal = array("h", [1000, -1000] * 20).tobytes()
    assert pcm16_rms(signal) == 1000.0


def test_pulse_whisper_requires_model_and_binary(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")

    assert not PulseWhisperSpeechToText(
        model_path=tmp_path / "missing-model.bin",
        executable=str(tmp_path / "missing-whisper"),
    ).is_available()
