from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from body.controller import (
    ArduinoSerialBodyController,
    BodyControlError,
    BodyController,
    CommandBodyController,
    LoggingBodyController,
    NullBodyController,
)
from orchestrator.services.fallback_client import FallbackRafikiClient
from orchestrator.services.llm_client import (
    LLMClientError,
    RafikiDecision,
    RafikiLLMClient,
)
from voice.stt import (
    PulseWhisperSpeechToText,
    SpeechToTextError,
)
from voice.tts import EspeakTTS, TextToSpeechError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Talk with Rafiki from the Raspberry Pi terminal."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="rafiki-local")
    parser.add_argument("--llm-max-tokens", type=int, default=96)
    parser.add_argument("--language", default="fr")
    parser.add_argument(
        "--input",
        choices=["text", "pulse"],
        default="text",
    )
    parser.add_argument(
        "--whisper-model",
        default="models-local/whisper/ggml-base-q5_1.bin",
    )
    parser.add_argument(
        "--whisper-executable",
        default="tools/whisper.cpp/build/bin/whisper-cli",
    )
    parser.add_argument("--whisper-threads", type=int, default=4)
    parser.add_argument("--stt-device")
    parser.add_argument("--pulse-device", default="@DEFAULT_SOURCE@")
    parser.add_argument("--pulse-recorder", default="parecord")
    parser.add_argument(
        "--stt-audio-filter",
        default=(
            "highpass=f=80,"
            "lowpass=f=7600,"
            "afftdn=nf=-30,"
            "volume=0.9"
        ),
    )
    parser.add_argument("--stt-timeout", type=float, default=10.0)
    parser.add_argument("--stt-phrase-time-limit", type=float, default=8.0)
    parser.add_argument("--stt-speech-threshold", type=float, default=260.0)
    parser.add_argument("--stt-end-silence", type=float, default=0.8)
    parser.add_argument("--ffmpeg-executable", default="ffmpeg")
    parser.add_argument("--no-voice", action="store_true")
    parser.add_argument("--no-fallback", action="store_true")
    parser.add_argument("--no-start-greeting", action="store_true")
    parser.add_argument(
        "--body-driver",
        choices=["none", "log", "arduino", "command"],
        default="none",
    )
    parser.add_argument("--body-port", default="/dev/ttyACM0")
    parser.add_argument("--body-baudrate", type=int, default=115200)
    parser.add_argument("--body-timeout", type=float, default=1.0)
    parser.add_argument("--body-startup-delay", type=float, default=8.0)
    parser.add_argument("--body-command")
    parser.add_argument("--tts-voice", default="fr-fr")
    parser.add_argument("--tts-speed", type=int, default=155)
    parser.add_argument("--tts-pitch", type=int, default=45)
    return parser


def build_tts(args: argparse.Namespace) -> EspeakTTS:
    return EspeakTTS(
        voice=args.tts_voice,
        speed=args.tts_speed,
        pitch=args.tts_pitch,
        enabled=not args.no_voice,
    )


def build_stt(args: argparse.Namespace) -> PulseWhisperSpeechToText:
    if args.input == "pulse":
        return PulseWhisperSpeechToText(
            model_path=args.whisper_model,
            executable=args.whisper_executable,
            device=args.pulse_device,
            recorder=args.pulse_recorder,
            ffmpeg_executable=args.ffmpeg_executable,
            language=args.language,
            threads=args.whisper_threads,
            audio_filter=args.stt_audio_filter or None,
            speech_threshold=args.stt_speech_threshold,
            end_silence=args.stt_end_silence,
        )

    return PulseWhisperSpeechToText(model_path=args.whisper_model)


def build_body(args: argparse.Namespace) -> BodyController:
    if args.body_driver == "log":
        return LoggingBodyController()

    if args.body_driver == "arduino":
        return ArduinoSerialBodyController(
            port=args.body_port,
            baudrate=args.body_baudrate,
            timeout=args.body_timeout,
            startup_delay=args.body_startup_delay,
        )

    if args.body_driver == "command":
        return CommandBodyController(args.body_command or "")

    return NullBodyController()


def perform_decision(
    decision: RafikiDecision,
    tts: EspeakTTS,
    body: BodyController,
) -> None:
    print(f"Rafiki > {decision.speech}")
    print(
        "Decision:",
        f"emotion={decision.emotion},",
        f"movement={decision.movement},",
        f"screen={decision.screen_mode}",
    )

    def start_body() -> None:
        try:
            body.apply(decision)
        except BodyControlError as exc:
            print(f"Rafiki: commande corps impossible: {exc}")

    def stop_body() -> None:
        try:
            body.stop_motion()
        except BodyControlError as exc:
            print(f"Rafiki: arret du corps impossible: {exc}")

    try:
        if tts.enabled:
            tts.speak(
                decision.speech,
                on_playback_start=start_body,
                on_playback_end=stop_body,
            )
        else:
            start_body()
            stop_body()
    except TextToSpeechError as exc:
        print(f"Rafiki: sortie vocale impossible: {exc}")
        stop_body()


def build_opening_decision() -> RafikiDecision:
    return RafikiDecision(
        speech="Salut ! Tu veux jouer ou discuter ?",
        emotion="happy",
        movement="swing",
        screen_mode="face",
        screen_content="",
    )


def main() -> int:
    args = build_parser().parse_args()
    llm_client = RafikiLLMClient(
        base_url=args.base_url,
        model=args.model,
        max_tokens=args.llm_max_tokens,
    )
    fallback_client = FallbackRafikiClient()
    tts = build_tts(args)
    stt = build_stt(args)
    body = build_body(args)

    use_fallback = False
    if llm_client.is_ready():
        print(f"Rafiki: LLM pret sur {args.base_url}.")
    elif args.no_fallback:
        print(f"Rafiki: llama-server n'est pas pret sur {args.base_url}.")
        return 2
    else:
        use_fallback = True
        print("Rafiki: llama-server n'est pas pret, mode secours active.")

    if not args.no_voice and not tts.is_available():
        print("Rafiki: moteur vocal indisponible, sortie vocale desactivee.")
        tts.enabled = False

    if args.input == "pulse" and not stt.is_available():
        print("Rafiki: entree vocale indisponible. Mode texte active.")
        args.input = "text"

    if not body.is_available():
        print("Rafiki: corps indisponible, mouvements desactives.")
        body = NullBodyController()
    else:
        try:
            body.prepare()
        except BodyControlError as exc:
            print(f"Rafiki: initialisation du corps impossible: {exc}")
            body = NullBodyController()

    if args.input == "pulse":
        print("Rafiki: parle apres le signal. Dis /quit ou Ctrl+C pour sortir.")
    else:
        print("Rafiki: ecris ton message. Tape /quit pour sortir.")

    history: list[dict[str, str]] = []

    try:
        try:
            if not args.no_start_greeting:
                perform_decision(build_opening_decision(), tts, body)

            while True:
                try:
                    if args.input == "pulse":
                        print("Toi > j'ecoute...")
                        user_message = stt.listen_once(
                            timeout=args.stt_timeout,
                            phrase_time_limit=args.stt_phrase_time_limit,
                        )
                        print(f"Toi > {user_message}")
                    else:
                        user_message = input("Toi > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                except SpeechToTextError as exc:
                    print(f"Rafiki: je n'ai pas bien entendu: {exc}")
                    continue

                if user_message.lower() in {"/quit", "/exit", "quit", "exit"}:
                    break

                if not user_message:
                    continue

                client = fallback_client if use_fallback else llm_client

                try:
                    decision = client.generate(
                        user_message,
                        language=args.language,
                        history=history,
                    )
                except LLMClientError as exc:
                    if args.no_fallback:
                        print(f"Rafiki: erreur LLM: {exc}")
                        continue

                    use_fallback = True
                    decision = fallback_client.generate(
                        user_message,
                        language=args.language,
                    )

                perform_decision(decision, tts, body)

                history.extend(
                    [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": decision.model_dump_json()},
                    ]
                )
        except KeyboardInterrupt:
            print()
    finally:
        try:
            body.stop_motion()
        except BodyControlError as exc:
            print(f"Rafiki: arret du corps impossible: {exc}")
        body.close()

    print("Rafiki: a bientot !")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
