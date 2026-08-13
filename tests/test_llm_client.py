import pytest

from orchestrator.services.llm_client import (
    LLMClientError,
    RafikiDecision,
    parse_rafiki_decision,
)


def test_parse_rafiki_decision_from_dict() -> None:
    decision = parse_rafiki_decision(
        {
            "speech": "Bonjour, on apprend ensemble ?",
            "emotion": "happy",
            "movement": "swing",
            "screen_mode": "learning",
            "screen_content": "Quiz animaux",
        }
    )

    assert isinstance(decision, RafikiDecision)
    assert decision.emotion == "happy"
    assert decision.screen_mode == "face"


def test_parse_rafiki_decision_from_markdown_json() -> None:
    decision = parse_rafiki_decision(
        """
        ```json
        {
          "speech": "Bonne question !",
          "emotion": "thinking",
          "movement": "none",
          "screen_mode": "text",
          "screen_content": "Je reflechis..."
        }
        ```
        """
    )

    assert decision.speech == "Bonne question !"
    assert decision.movement == "none"


def test_parse_rafiki_decision_extracts_json_from_extra_text() -> None:
    decision = parse_rafiki_decision(
        """
        Voici ma reponse:
        {
          "speech": "Bravo !",
          "emotion": "happy",
          "movement": "dance",
          "screen_mode": "face",
          "screen_content": ":)"
        }
        A bientot.
        """
    )

    assert decision.speech == "Bravo !"
    assert decision.movement == "dance"


def test_parse_rafiki_decision_rejects_invalid_json() -> None:
    with pytest.raises(LLMClientError):
        parse_rafiki_decision("Rafiki repond sans JSON.")


def test_parse_rafiki_decision_rejects_unknown_action() -> None:
    with pytest.raises(LLMClientError):
        parse_rafiki_decision(
            """
            {
              "speech": "Je decolle !",
              "emotion": "happy",
              "movement": "fly",
              "screen_mode": "face",
              "screen_content": ":)"
            }
            """
        )


def test_parse_rafiki_decision_replaces_forbidden_robot_intro() -> None:
    decision = parse_rafiki_decision(
        {
            "speech": "Je suis un robot compagnon éducatif pour vous aider.",
            "emotion": "happy",
            "movement": "none",
            "screen_mode": "text",
            "screen_content": "Bonjour",
        }
    )

    assert decision.speech == "Salut ! Tu veux jouer ou discuter ?"
    assert decision.screen_mode == "face"
    assert decision.screen_content == ""


def test_parse_rafiki_decision_keeps_quiz_text_only_for_question() -> None:
    decision = parse_rafiki_decision(
        {
            "speech": "Quel animal miaule ?",
            "emotion": "happy",
            "movement": "none",
            "screen_mode": "quiz",
            "screen_content": "Chat ou chien ?",
        }
    )

    assert decision.screen_mode == "quiz"
    assert decision.screen_content == "Chat ou chien ?"


def test_parse_rafiki_decision_keeps_complete_sentence() -> None:
    decision = parse_rafiki_decision(
        {
            "speech": (
                "Les monuments sont des bâtiments historiques qui symbolisent "
                "l'histoire et le patrimoine culturel de la région ou du pays."
            ),
            "emotion": "happy",
            "movement": "none",
            "screen_mode": "face",
            "screen_content": "",
        }
    )

    assert decision.speech == (
        "Les monuments sont des bâtiments historiques qui symbolisent "
        "l'histoire et le patrimoine culturel de la région ou du pays."
    )
