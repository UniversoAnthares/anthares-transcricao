import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app


VIDEO_ID = "dQw4w9WgXcQ"


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_invalid_video_id_is_rejected_before_external_calls(self):
        with patch("app.subprocess.run") as run:
            response = self.client.get("/transcricao?v=invalid")
        self.assertEqual(response.status_code, 400)
        run.assert_not_called()

    def test_missing_key_is_reported(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            response = self.client.get(f"/transcricao?v={VIDEO_ID}")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["erro"], "GROQ_API_KEY nao configurada")

    def test_missing_ytdlp_is_reported(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
            with patch("app.subprocess.run", side_effect=FileNotFoundError):
                response = self.client.get(f"/transcricao?v={VIDEO_ID}")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["erro"], "servico de download indisponivel")

    def test_successful_transcription(self):
        def fake_download(command, **kwargs):
            output_template = command[command.index("-o") + 1]
            Path(output_template.replace("%(ext)s", "m4a")).write_bytes(b"audio")
            return SimpleNamespace(returncode=0, stderr="")

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
            with patch("app.subprocess.run", side_effect=fake_download):
                with patch("app.requests.post", return_value=FakeResponse({"text": "Olá"})) as post:
                    response = self.client.get(f"/transcricao?v={VIDEO_ID}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"texto": "Olá"})
        self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "Bearer test-key"})

    def test_non_object_groq_payload_is_rejected(self):
        def fake_download(command, **kwargs):
            output_template = command[command.index("-o") + 1]
            Path(output_template.replace("%(ext)s", "m4a")).write_bytes(b"audio")
            return SimpleNamespace(returncode=0, stderr="")

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
            with patch("app.subprocess.run", side_effect=fake_download):
                with patch("app.requests.post", return_value=FakeResponse([])):
                    response = self.client.get(f"/transcricao?v={VIDEO_ID}")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["erro"], "resposta invalida da groq")


if __name__ == "__main__":
    unittest.main()
