import mimetypes
import os
import re
import shutil
import subprocess
import tempfile

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

MAX_AUDIO_BYTES = 24 * 1024 * 1024
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3"


def _read_groq_api_key():
    return (os.environ.get("GROQ_API_KEY") or "").strip()


@app.route("/transcricao")
def transcricao():
    video_id = request.args.get("v", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return jsonify({"error": "video_id invalido"}), 400

    api_key = _read_groq_api_key()
    if not api_key:
        return jsonify({"error": "transcricao indisponivel"}), 503

    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmp:
        output_template = os.path.join(tmp, "audio.%(ext)s")
        deno = shutil.which("deno")
        if not deno:
            return jsonify({"error": "transcricao indisponivel"}), 503

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--js-runtimes",
            f"deno:{deno}",
            "--retries",
            "8",
            "--fragment-retries",
            "8",
            "--extractor-retries",
            "3",
            "--socket-timeout",
            "30",
            "-f",
            "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
            "--max-filesize",
            str(MAX_AUDIO_BYTES),
            "-o",
            output_template,
            url,
        ]

        try:
            resultado = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
                check=False,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return jsonify({"error": "timeout"}), 504
        except OSError:
            return jsonify({"error": "transcricao indisponivel"}), 503

        if resultado.returncode != 0:
            return jsonify({"error": "transcricao indisponivel"}), 502

        arquivos = [
            nome
            for nome in sorted(os.listdir(tmp))
            if not nome.endswith(".part") and os.path.isfile(os.path.join(tmp, nome))
        ]
        if not arquivos:
            return jsonify({"error": "audio nao encontrado"}), 404

        caminho_audio = os.path.join(tmp, arquivos[0])
        tamanho = os.path.getsize(caminho_audio)
        if tamanho > MAX_AUDIO_BYTES:
            return jsonify({"error": "audio grande demais"}), 413

        extensao = os.path.splitext(caminho_audio)[1].lower() or ".m4a"
        mime = mimetypes.guess_type(caminho_audio)[0] or "application/octet-stream"

        try:
            with open(caminho_audio, "rb") as handle:
                resposta = requests.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (f"audio{extensao}", handle, mime)},
                    data={"model": GROQ_MODEL, "language": "pt"},
                    timeout=90,
                )
        except requests.RequestException:
            return jsonify({"error": "transcricao indisponivel"}), 502

        if resposta.status_code != 200:
            return jsonify({"error": "transcricao indisponivel"}), 502

        try:
            payload = resposta.json()
        except ValueError:
            return jsonify({"error": "transcricao indisponivel"}), 502

        texto = payload.get("text", "")
        if not texto:
            return jsonify({"error": "transcricao vazia"}), 404

        return jsonify({"texto": texto})


@app.route("/")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
