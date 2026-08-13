from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import wave
from array import array
from pathlib import Path


class SpeechToTextError(RuntimeError):
    """Raised when Rafiki cannot listen through the configured STT engine."""


def pcm16_rms(data: bytes) -> float:
    """Return the RMS level of little-endian signed 16-bit PCM audio."""
    if len(data) < 2:
        return 0.0

    samples = array("h")
    samples.frombytes(data[: len(data) - (len(data) % 2)])
    if not samples:
        return 0.0

    square_sum = sum(sample * sample for sample in samples)
    return (square_sum / len(samples)) ** 0.5


class PulseWhisperSpeechToText:
    """Record one PulseAudio utterance, then transcribe it with whisper.cpp."""

    def __init__(
        self,
        model_path: str | Path,
        executable: str = "tools/whisper.cpp/build/bin/whisper-cli",
        device: str = "@DEFAULT_SOURCE@",
        recorder: str = "parecord",
        ffmpeg_executable: str = "ffmpeg",
        language: str = "fr",
        threads: int = 4,
        sample_rate: int = 16000,
        raw_sample_rate: int = 48000,
        raw_channels: int = 2,
        chunk_duration: float = 0.2,
        audio_filter: str | None = None,
        speech_threshold: float = 260.0,
        end_silence: float = 0.8,
        min_speech_duration: float = 0.3,
    ) -> None:
        self.model_path = Path(model_path)
        self.executable = executable
        self.device = device
        self.recorder = recorder
        self.ffmpeg_executable = ffmpeg_executable
        self.language = language
        self.threads = threads
        self.sample_rate = sample_rate
        self.raw_sample_rate = raw_sample_rate
        self.raw_channels = raw_channels
        self.chunk_duration = chunk_duration
        self.audio_filter = audio_filter
        self.speech_threshold = speech_threshold
        self.end_silence = end_silence
        self.min_speech_duration = min_speech_duration

    def is_available(self) -> bool:
        return (
            self.model_path.exists()
            and Path(self.executable).exists()
            and shutil.which(self.recorder) is not None
            and shutil.which(self.ffmpeg_executable) is not None
            and bool(self.device.strip())
        )

    def listen_once(
        self,
        timeout: float | None = None,
        phrase_time_limit: float = 8.0,
    ) -> str:
        if not self.is_available():
            raise SpeechToTextError("Whisper input is not fully installed")

        pcm = self._record_utterance(timeout, phrase_time_limit)
        with tempfile.TemporaryDirectory(prefix="rafiki-stt-") as temp_dir:
            wav_path = Path(temp_dir) / "utterance.wav"
            output_base = Path(temp_dir) / "transcript"
            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm)

            command = [
                self.executable,
                "--model",
                str(self.model_path),
                "--file",
                str(wav_path),
                "--language",
                self.language,
                "--threads",
                str(self.threads),
                "--no-timestamps",
                "--output-txt",
                "--output-file",
                str(output_base),
                "--suppress-nst",
                "--no-prints",
            ]
            try:
                subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as exc:
                raise SpeechToTextError(f"Whisper transcription failed: {exc}") from exc

            transcript_path = output_base.with_suffix(".txt")
            if not transcript_path.exists():
                raise SpeechToTextError("Whisper produced no transcript")

            text = " ".join(transcript_path.read_text().strip().split())
            if not text:
                raise SpeechToTextError("No speech recognized")
            return text

    def _record_utterance(
        self,
        timeout: float | None,
        phrase_time_limit: float,
    ) -> bytes:
        recorder_command = [
            self.recorder,
            "--device",
            self.device,
            "--raw",
            "--format",
            "s16le",
            "--channels",
            str(self.raw_channels),
            "--rate",
            str(self.raw_sample_rate),
        ]
        filter_chain = self.audio_filter or "highpass=f=80,lowpass=f=7600"
        ffmpeg_command = [
            self.ffmpeg_executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "s16le",
            "-ar",
            str(self.raw_sample_rate),
            "-ac",
            str(self.raw_channels),
            "-i",
            "pipe:0",
            "-af",
            filter_chain,
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            str(self.sample_rate),
            "pipe:1",
        ]
        recorder_process = subprocess.Popen(
            recorder_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdin=recorder_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if recorder_process.stdout is not None:
            recorder_process.stdout.close()

        chunk_size = max(3200, int(self.sample_rate * 2 * self.chunk_duration))
        started_at = time.monotonic()
        speech_started_at: float | None = None
        last_voice_at: float | None = None
        chunks: list[bytes] = []

        try:
            if ffmpeg_process.stdout is None:
                raise SpeechToTextError("ffmpeg did not expose an audio stream")

            while True:
                data = ffmpeg_process.stdout.read(chunk_size)
                now = time.monotonic()
                if not data:
                    raise SpeechToTextError("Pulse audio stream ended unexpectedly")

                level = pcm16_rms(data)
                if level >= self.speech_threshold:
                    if speech_started_at is None:
                        speech_started_at = now
                    last_voice_at = now

                if speech_started_at is not None:
                    chunks.append(data)

                if speech_started_at is None:
                    if timeout is not None and now - started_at >= timeout:
                        raise SpeechToTextError("No speech recognized before timeout")
                    continue

                if now - speech_started_at >= phrase_time_limit:
                    break
                if (
                    last_voice_at is not None
                    and now - speech_started_at >= self.min_speech_duration
                    and now - last_voice_at >= self.end_silence
                ):
                    break
        finally:
            for process in (ffmpeg_process, recorder_process):
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()

        if not chunks:
            raise SpeechToTextError("No speech recorded")
        return b"".join(chunks)

