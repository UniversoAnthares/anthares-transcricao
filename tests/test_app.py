import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app as service


class TranscricaoContractTests(unittest.TestCase):
    def setUp(self):
        self.client = service.app.test_client()
        self.original_key = service.GROQ_API_KEY
        service.GROQ_API_KEY = "test-only-key"

    def tearDown(self):
        service.GROQ_API_KEY = self.original_key

    def test_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_invalid_video_id_does_not_download(self):
        with patch.object(service.subprocess, "run") as run:
            response = self.client.get("/transcricao?v=invalid")
        self.assertEqual(response.status_code, 400)
        run.assert_not_called()

    def test_success_uses_download_limit_and_returns_text(self):
        def fake_run(command, **_kwargs):
            output_template = command[command.index("-o") + 1]
            audio_path = output_template.replace("%(ext)s", "m4a")
            with open(audio_path, "wb") as handle:
                handle.write(b"audio")
            return SimpleNamespace(returncode=0, stderr="")

        groq_response = SimpleNamespace(
            status_code=200,
            text='{"text":"olá"}',
            json=lambda: {"text": "olá"},
        )
        with patch.object(service.subprocess, "run", side_effect=fake_run) as run:
            with patch.object(service.requests, "post", return_value=groq_response):
                response = self.client.get("/transcricao?v=dQw4w9WgXcQ")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"texto": "olá"})
        command = run.call_args.args[0]
        self.assertIn("--max-filesize", command)
        self.assertEqual(command[command.index("--max-filesize") + 1], str(service.MAX_AUDIO_BYTES))

    def test_upstream_failure_does_not_echo_details(self):
        def failed_download(_command, **_kwargs):
            return SimpleNamespace(returncode=1, stderr="SECRET_UPSTREAM_DETAIL")

        with patch.object(service.subprocess, "run", side_effect=failed_download):
            response = self.client.get("/transcricao?v=dQw4w9WgXcQ")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(b"SECRET_UPSTREAM_DETAIL", response.data)

    def test_groq_failure_does_not_echo_body(self):
        def successful_download(command, **_kwargs):
            output_template = command[command.index("-o") + 1]
            with open(output_template.replace("%(ext)s", "m4a"), "wb") as handle:
                handle.write(b"audio")
            return SimpleNamespace(returncode=0, stderr="")

        groq_response = SimpleNamespace(status_code=500, text="SECRET_GROQ_BODY")
        with patch.object(service.subprocess, "run", side_effect=successful_download):
            with patch.object(service.requests, "post", return_value=groq_response):
                response = self.client.get("/transcricao?v=dQw4w9WgXcQ")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(b"SECRET_GROQ_BODY", response.data)


if __name__ == "__main__":
    unittest.main()
