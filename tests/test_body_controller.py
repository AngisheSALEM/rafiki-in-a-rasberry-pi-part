from orchestrator.services.llm_client import RafikiDecision
from body.controller import build_body_commands


def make_decision(
    *,
    emotion: str = "happy",
    movement: str = "none",
    screen_mode: str = "face",
    screen_content: str = ":)",
) -> RafikiDecision:
    return RafikiDecision(
        speech="Bonjour",
        emotion=emotion,
        movement=movement,
        screen_mode=screen_mode,
        screen_content=screen_content,
    )


def test_body_uses_emotion_for_face_behavior() -> None:
    plan = build_body_commands(make_decision(emotion="surprised"))

    assert plan.commands == ("S0", "E6", "SHOW_EYES")


def test_body_movement_overrides_emotion() -> None:
    plan = build_body_commands(make_decision(emotion="sad", movement="dance"))

    assert plan.commands == ("B2",)


def test_body_keeps_moving_face_and_servos_synchronized() -> None:
    plan = build_body_commands(make_decision(emotion="surprised", movement="swing"))

    assert plan.commands == ("B6",)


def test_body_text_mode_sends_screen_content() -> None:
    plan = build_body_commands(
        make_decision(
            emotion="thinking",
            screen_mode="text",
            screen_content="Je reflechis...\nEncore un instant.",
        )
    )

    assert plan.commands == ("S0", "TEXT:Je reflechis... Encore un instant.")


def test_body_text_mode_without_content_keeps_face() -> None:
    plan = build_body_commands(
        make_decision(
            screen_mode="text",
            screen_content="",
        )
    )

    assert plan.commands == ("S0", "E0", "SHOW_EYES")


def test_body_learning_mode_keeps_emotional_face() -> None:
    plan = build_body_commands(
        make_decision(
            emotion="thinking",
            screen_mode="learning",
            screen_content="Un texte que le modele ne doit pas afficher.",
        )
    )

    assert plan.commands == ("S0", "E4", "SHOW_EYES")


def test_body_stop_stops_behavior() -> None:
    plan = build_body_commands(make_decision(movement="stop"))

    assert plan.commands == ("S0", "E0", "SHOW_EYES")
