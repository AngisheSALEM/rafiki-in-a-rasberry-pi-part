from __future__ import annotations

from orchestrator.services.llm_client import RafikiDecision


class FallbackRafikiClient:
    """Small offline responder used only when the real LLM server is unavailable."""

    def is_ready(self) -> bool:
        return True

    def generate(
        self,
        user_message: str,
        language: str = "fr",
        history: list[dict[str, str]] | None = None,
    ) -> RafikiDecision:
        message = user_message.strip()
        normalized = message.lower()

        if not message:
            speech = "Je suis la. Ecris-moi une petite phrase quand tu veux."
            emotion = "neutral"
            screen_mode = "face"
        elif any(word in normalized for word in ["quiz", "question", "jeu"]):
            speech = (
                "D'accord ! Petite question : quel animal miaule, le chat ou le chien ?"
            )
            emotion = "happy"
            screen_mode = "quiz"
        elif any(word in normalized for word in ["triste", "peur", "mal"]):
            speech = (
                "Je suis avec toi. On peut respirer doucement ensemble, une fois."
            )
            emotion = "sad"
            screen_mode = "face"
        elif any(word in normalized for word in ["bonjour", "salut", "coucou"]):
            speech = "Bonjour ! Je suis Rafiki. Je suis content de te parler."
            emotion = "happy"
            screen_mode = "face"
        else:
            speech = (
                "J'ai bien compris. Mon grand cerveau local arrive bientot, "
                "mais je peux deja parler avec toi."
            )
            emotion = "thinking"
            screen_mode = "text"

        return RafikiDecision(
            speech=speech,
            emotion=emotion,
            movement="none",
            screen_mode=screen_mode,
            screen_content=speech,
        )
