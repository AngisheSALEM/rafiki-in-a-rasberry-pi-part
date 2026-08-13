from __future__ import annotations

import json
from typing import Literal

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError


Emotion = Literal[
    "neutral",
    "happy",
    "sad",
    "surprised",
    "thinking",
]

Movement = Literal[
    "none",
    "swing",
    "dance",
    "walk_forward",
    "walk_backward",
    "turn_left",
    "turn_right",
    "stop",
]

ScreenMode = Literal[
    "face",
    "text",
    "learning",
    "quiz",
]


class RafikiDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speech: str = Field(max_length=180)
    emotion: Emotion
    movement: Movement
    screen_mode: ScreenMode
    screen_content: str = Field(max_length=120)


RAFIKI_SCHEMA = {
    "type": "object",
    "properties": {
        "speech": {
            "type": "string",
            "maxLength": 180,
        },
        "emotion": {
            "type": "string",
            "enum": [
                "neutral",
                "happy",
                "sad",
                "surprised",
                "thinking",
            ],
        },
        "movement": {
            "type": "string",
            "enum": [
                "none",
                "swing",
                "dance",
                "walk_forward",
                "walk_backward",
                "turn_left",
                "turn_right",
                "stop",
            ],
        },
        "screen_mode": {
            "type": "string",
            "enum": [
                "face",
                "text",
                "learning",
                "quiz",
            ],
        },
        "screen_content": {
            "type": "string",
            "maxLength": 120,
        },
    },
    "required": [
        "speech",
        "emotion",
        "movement",
        "screen_mode",
        "screen_content",
    ],
    "additionalProperties": False,
}


class LLMClientError(RuntimeError):
    """Erreur lors de la communication avec llama-server."""

def parse_rafiki_decision(raw_content: object) -> RafikiDecision:
    if isinstance(raw_content, dict):
        return normalize_rafiki_decision(RafikiDecision.model_validate(raw_content))

    if not isinstance(raw_content, str):
        raise LLMClientError(
            f"Type de réponse inattendu : {type(raw_content).__name__}"
        )

    content = raw_content.strip()

    # Retirer d'éventuelles balises Markdown.
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    # Premier essai : la réponse entière est du JSON.
    try:
        return normalize_rafiki_decision(RafikiDecision.model_validate_json(content))
    except ValidationError:
        pass

    # Deuxième essai : extraire l'objet JSON si le modèle
    # a ajouté du texte avant ou après.
    start = content.find("{")
    end = content.rfind("}")

    if start != -1 and end > start:
        json_part = content[start : end + 1]

        try:
            return normalize_rafiki_decision(
                RafikiDecision.model_validate_json(json_part)
            )
        except ValidationError as exc:
            raise LLMClientError(
                "Objet JSON présent mais invalide. "
                f"Réponse brute : {content[:400]!r}"
            ) from exc

    raise LLMClientError(
        "Le modèle n'a retourné aucun JSON. "
        f"Réponse brute : {content[:400]!r}"
    )


def normalize_rafiki_decision(decision: RafikiDecision) -> RafikiDecision:
    speech = _shorten_speech(decision.speech)
    screen_content = " ".join(decision.screen_content.strip().split())
    screen_mode = decision.screen_mode

    forbidden_fragments = [
        "robot compagnon éducatif",
        "robot compagnon educatif",
        "pour vous aider",
    ]
    if any(fragment in speech.lower() for fragment in forbidden_fragments):
        speech = "Salut ! Tu veux jouer ou discuter ?"
        screen_mode = "face"
        screen_content = ""

    if screen_mode == "learning":
        screen_mode = "face"
        screen_content = ""

    if screen_mode == "quiz":
        quiz_text = screen_content or speech
        if "?" not in quiz_text:
            screen_mode = "face"
            screen_content = ""
        else:
            screen_content = quiz_text

    if screen_mode == "text" and not screen_content:
        screen_mode = "face"

    if screen_mode == "face":
        screen_content = ""

    return decision.model_copy(
        update={
            "speech": speech,
            "screen_mode": screen_mode,
            "screen_content": screen_content,
        }
    )


def _shorten_speech(text: str) -> str:
    first_sentence = " ".join(text.strip().split())
    for separator in [". ", "! ", "? "]:
        if separator in first_sentence:
            first_sentence = first_sentence.split(separator, 1)[0] + separator.strip()
            break

    return first_sentence

class RafikiLLMClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        model: str = "rafiki-local",
        timeout: float = 120.0,
        max_tokens: int = 96,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def is_ready(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=3,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def generate(
        self,
        user_message: str,
        language: str = "fr",
        history: list[dict[str, str]] | None = None,
    ) -> RafikiDecision:
        system_prompt = (
            "Tu es Rafiki, un robot compagnon éducatif destiné aux enfants "
            "de 5 à 10 ans. Tes réponses doivent être courtes, simples, "
            "naturelles, bienveillantes et adaptées à l'âge de l'enfant. "
            "Tu tutoies toujours l'enfant. "
            "Ne dis jamais que tu es un robot compagnon éducatif. "
            "Ne commence pas par répéter le nom Rafiki. "
            f"Réponds principalement dans la langue suivante : {language}. "
            "Ne demande jamais au robot d'exécuter une action dangereuse. "
            "Choisis uniquement les émotions, mouvements et modes d'écran "
            "autorisés par le schéma JSON. "
            "Utilise screen_mode face par défaut pour montrer une émotion. "
            "Utilise screen_mode learning sans texte pour une explication simple. "
            "Utilise screen_mode text seulement si l'enfant demande d'afficher, "
            "lire, épeler, compter ou retenir une information. "
            "Utilise screen_mode quiz seulement si tu poses une vraie question. "
            "Dans text ou quiz, screen_content doit contenir le texte utile. "
            "Dans face ou learning, screen_content doit être vide. "
            "Utilise movement none par défaut; choisis dance, swing ou turn_left "
            "seulement pour une réaction courte et joyeuse. "
            "Tu dois répondre uniquement avec un objet JSON valide, compact, "
            "sans Markdown, sans explication et sans texte autour. "
            "Le champ speech doit contenir une seule phrase courte, "
            "avec au maximum 14 mots. "
            "Le champ screen_content doit rester tres court. "
            "Ne répète jamais la même idée, le même groupe de mots ou la "
            "même phrase. Si tu racontes une blague, elle doit tenir en une "
            "seule phrase simple."
        )

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        if history:
            messages.extend(history[-6:])

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": self.max_tokens,
            "frequency_penalty": 0.4,
            "repeat_penalty": 1.18,
            "stream": False,
            "chat_template_kwargs": {
                "enable_thinking": False,
            },
            "response_format": {
                "type": "json_object",
                "schema": RAFIKI_SCHEMA,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            api_result = response.json()
            raw_content = api_result["choices"][0]["message"]["content"]

            return parse_rafiki_decision(raw_content)

        except (
            requests.RequestException,
            KeyError,
            IndexError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise LLMClientError(
                f"Réponse invalide de llama-server : {exc}"
            ) from exc
