from orchestrator.services.fallback_client import FallbackRafikiClient


def test_fallback_client_returns_valid_decision() -> None:
    decision = FallbackRafikiClient().generate("Bonjour Rafiki")

    assert decision.speech
    assert decision.emotion == "happy"
    assert decision.movement == "none"
    assert decision.screen_mode == "face"
