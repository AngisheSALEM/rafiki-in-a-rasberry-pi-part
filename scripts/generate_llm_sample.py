from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.services.llm_client import RafikiLLMClient


def main() -> int:
    client = RafikiLLMClient()

    if not client.is_ready():
        print("llama-server n'est pas pret.")
        return 2

    decision = client.generate(
        "Donne-moi un petit quiz sur les animaux.",
        language="fr",
    )

    print(decision.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
