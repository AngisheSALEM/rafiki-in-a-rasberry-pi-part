import pytest
from fastapi.testclient import TestClient

from orchestrator.server import app, state


@pytest.fixture
def client():
    # Clear state before each test
    state.body_queue.clear()
    state.latest_body_status = {
        "connected": False,
        "last_updated": 0,
        "body_port": None,
        "last_command_id": None,
        "last_action": None,
        "serial_commands": [],
        "error": None,
    }
    state.latest_vision_frame = None
    return TestClient(app)


def test_root_and_health(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["service"] == "Rafiki Orchestrator Bridge Server"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "online"


def test_body_pull_empty_queue(client):
    res = client.get("/api/body/next")
    assert res.status_code == 200
    assert res.json() == {"command": None}


def test_body_enqueue_and_pull(client):
    # Enqueue a body command
    res = client.post("/api/body/enqueue", json={"action": "set_expression", "params": {"emotion": "happy"}})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "enqueued"
    cmd_id = data["command_id"]

    # Pull the next body command
    pull_res = client.get("/api/body/next")
    assert pull_res.status_code == 200
    cmd_payload = pull_res.json()["command"]
    assert cmd_payload["id"] == cmd_id
    assert cmd_payload["action"] == "set_expression"
    assert cmd_payload["params"] == {"emotion": "happy"}

    # Queue should be empty now
    pull_empty = client.get("/api/body/next")
    assert pull_empty.json() == {"command": None}


def test_body_status_reporting(client):
    status_payload = {
        "status": {
            "connected": True,
            "body_port": "/dev/ttyACM0",
            "last_command_id": "abc12345",
            "last_action": "set_expression",
            "serial_commands": ["E0", "SHOW_EYES"],
        }
    }
    res = client.post("/api/body/status", json=status_payload)
    assert res.status_code == 200

    status_get = client.get("/api/body/status")
    assert status_get.status_code == 200
    assert status_get.json()["online"] is True
    assert status_get.json()["status"]["connected"] is True


def test_vision_registration_and_upload(client):
    reg = client.post("/api/vision/register", json={"vision_url": "http://10.20.20.150:8000"})
    assert reg.status_code == 200
    assert reg.json()["vision_url"] == "http://10.20.20.150:8000"

    upload = client.post("/api/vision/upload", json={
        "image_base64": "SGVsbG8gV29ybGQ=",
        "width": 1280,
        "height": 720,
        "camera_type": "ov5647"
    })
    assert upload.status_code == 200

    latest = client.get("/api/vision/latest")
    assert latest.status_code == 200
    assert latest.json()["image_base64"] == "SGVsbG8gV29ybGQ="


def test_orchestration_step(client):
    res = client.post("/api/orchestration/step", json={
        "user_message": "Salue l'enfant avec joie",
        "include_vision": False,
        "language": "fr"
    })
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "speech" in body["decision"]
    assert len(body["enqueued_body_commands"]) > 0

    # Verify that commands were queued in body_queue for body_pull_client.py
    next_cmd = client.get("/api/body/next").json()["command"]
    assert next_cmd is not None
    assert next_cmd["action"] in ["set_expression", "motor_gesture", "screen_text"]
