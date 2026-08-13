import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Ensure rafiki-vision-rasberry-pi is in path for imports
vision_repo = Path(__file__).resolve().parents[2] / "rafiki-vision-rasberry-pi"
if str(vision_repo) not in sys.path:
    sys.path.insert(0, str(vision_repo))

from rpi_vision.client.vision_pusher import (
    register_camera_service,
    push_single_frame,
    run_pusher,
)


class TestVisionPusher(unittest.TestCase):

    @patch("requests.post")
    def test_register_camera_service(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = register_camera_service("http://10.20.20.224:7860", "http://localhost:8000")
        self.assertTrue(res)

    @patch("requests.post")
    @patch("requests.get")
    def test_push_single_frame(self, mock_get, mock_post):
        mock_cap_resp = MagicMock()
        mock_cap_resp.status_code = 200
        mock_cap_resp.json.return_value = {
            "data_uri": "data:image/jpeg;base64,SGVsbG8=",
            "metadata": {"width": 1280, "height": 720, "camera_type": "ov5647"},
        }
        mock_get.return_value = mock_cap_resp

        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 200
        mock_post.return_value = mock_upload_resp

        res = push_single_frame("http://10.20.20.224:7860", "http://localhost:8000")
        self.assertTrue(res)

    @patch("rpi_vision.client.vision_pusher.push_single_frame")
    @patch("rpi_vision.client.vision_pusher.register_camera_service")
    def test_run_pusher_loop(self, mock_register, mock_push):
        mock_register.return_value = True
        mock_push.return_value = True

        run_pusher(
            server_url="http://10.20.20.224:7860",
            local_vision_url="http://localhost:8000",
            push_interval=0.01,
            retry_interval=0.01,
            max_loops=3,
        )
        self.assertEqual(mock_register.call_count, 1)
        self.assertEqual(mock_push.call_count, 3)


if __name__ == "__main__":
    unittest.main()
