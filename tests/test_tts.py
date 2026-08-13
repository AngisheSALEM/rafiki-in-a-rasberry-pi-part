import subprocess

import pytest

from voice.tts import EspeakTTS, TextToSpeechError, prepare_spoken_text


def test_tts_skips_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, check: calls.append(command))

    EspeakTTS().speak("   ")

    assert calls == []


def test_tts_runs_espeak_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(subprocess, "run", lambda command, check: calls.append(command))

    EspeakTTS(voice="fr-fr", speed=140, pitch=50).speak("Bonjour")

    assert calls == [
        ["espeak-ng", "-v", "fr-fr", "-s", "140", "-p", "50", "Bonjour"]
    ]


def test_tts_reports_missing_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda executable: None)

    with pytest.raises(TextToSpeechError):
        EspeakTTS().speak("Bonjour")


def test_prepare_spoken_text_shortens_and_punctuates() -> None:
    text = prepare_spoken_text(
        "Voici une phrase beaucoup trop longue pour une voix de robot qui doit "
        "rester claire pendant une demonstration devant les enfants",
        max_words=8,
    )

    assert text == "Voici une phrase beaucoup trop longue pour une."


def test_prepare_spoken_text_does_not_truncate_by_default() -> None:
    text = "Cette phrase doit etre prononcee entierement meme si elle est assez longue"

    assert prepare_spoken_text(text) == f"{text}."
