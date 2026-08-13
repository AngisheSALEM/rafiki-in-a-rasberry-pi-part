from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.services.llm_client import RafikiLLMClient


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_LLAMA_SERVER = Path("/home/admin/llama.cpp/build/bin/llama-server")
DEFAULT_MODELS_DIR = Path("/home/admin/llama.cpp/models")
MIN_CHAT_MODEL_BYTES = 100 * 1024 * 1024


def find_llama_server() -> Path | None:
    executable = shutil.which("llama-server")
    if executable:
        return Path(executable)

    if DEFAULT_LLAMA_SERVER.exists():
        return DEFAULT_LLAMA_SERVER

    return None


def find_gguf_models(models_dir: Path) -> list[Path]:
    if not models_dir.exists():
        return []

    return sorted(models_dir.glob("*.gguf"), key=lambda path: path.stat().st_size)


def format_size(path: Path) -> str:
    size_mb = path.stat().st_size / (1024 * 1024)
    return f"{size_mb:.1f} MB"


def print_llama_cache(server_path: Path | None) -> None:
    if not server_path:
        return

    try:
        result = subprocess.run(
            [str(server_path), "--cache-list"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return

    cache_lines = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("number of models")
    ]
    if not cache_lines:
        return

    print("llama.cpp cached models:")
    for line in cache_lines:
        print(f"  {line}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the local Rafiki LLM server and GGUF model files."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    args = parser.parse_args()

    server_path = find_llama_server()
    if server_path:
        print(f"llama-server: found at {server_path}")
    else:
        print("llama-server: not found in PATH or /home/admin/llama.cpp/build/bin")

    print_llama_cache(server_path)

    models = find_gguf_models(args.models_dir)
    chat_models = [
        model for model in models if model.stat().st_size >= MIN_CHAT_MODEL_BYTES
    ]

    if chat_models:
        print("GGUF chat model candidates:")
        for model in chat_models:
            print(f"  - {model} ({format_size(model)})")
    elif models:
        print("GGUF files found, but they look too small to be chat models:")
        for model in models:
            print(f"  - {model} ({format_size(model)})")
    else:
        print(f"GGUF models: none found in {args.models_dir}")

    client = RafikiLLMClient(base_url=args.base_url)
    if client.is_ready():
        print(f"server health: ready at {args.base_url}")
        return 0

    print(f"server health: not ready at {args.base_url}")
    if server_path and chat_models:
        print("Example launch command:")
        print(
            f"  {server_path} --model {chat_models[-1]} "
            "--alias rafiki-local --host 127.0.0.1 --port 8080"
        )

    try:
        requests.get(f"{args.base_url.rstrip('/')}/health", timeout=3)
    except requests.RequestException as exc:
        print(f"health check detail: {exc}")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
