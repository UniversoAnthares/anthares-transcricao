import mimetypes
import os
import re
import shutil
import subprocess
import tempfile

import requests
from flask import Flask, jsonify, request
from groq_resilience import Circuit, CircuitOpen, normalize_transcription

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3"
MAX_AUDIO_BYTES = 24 * 1024 * 1024
BREAKER = Circuit()
BREAKER_SCOPE = "groq-stt"


@app.route("/transcricao")
def transcricao():
    video_id = request.args.get("v", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return jsonify({"erro": "video_id invalido"}), 400

    if not GROQ_API_KEY:
        return jsonify({"erro": "GROQ_API_KEY nao configurada"}), 503

    try:
        BREAKER.check(BREAKER_SCOPE)
    except CircuitOpen as exc:
        return jsonify({"erro": "transcricao indisponivel",
                        "categoria": exc.reason}), 503

    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmp:
        saida = os.path.join(tmp, "audio.%(ext)s")
        deno = shutil.which("deno")
        if not deno:
            return jsonify({"erro": "runtime javascript do youtube indisponivel"}), 503
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--js-runtimes", f"deno:{deno}",
            "--retries", "8",
            "--fragment-retries", "8",
            "--extractor-retries", "3",
            "--socket-timeout", "30",
            "-f", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
            "--max-filesize", str(MAX_AUDIO_BYTES),
            "-o", saida,
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
            return jsonify({"erro": "timeout"}), 504
        except OSError:
            return jsonify({"erro": "servico de download indisponivel"}), 503

        if resultado.returncode != 0:
            return jsonify({
                "erro": "download falhou",
                "detalhe": "o provedor de vídeo não retornou áudio utilizável",
            }), 502

        arquivos = [
            f for f in os.listdir(tmp)
            if not f.endswith(".part") and os.path.isfile(os.path.join(tmp, f))
        ]
        if not arquivos:
            return jsonify({"erro": "sem audio"}), 404

        caminho_audio = os.path.join(tmp, arquivos[0])
        tamanho = os.path.getsize(caminho_audio)
        if tamanho > MAX_AUDIO_BYTES:
            return jsonify({"erro": "audio grande demais"}), 413

        extensao = os.path.splitext(caminho_audio)[1].lower()
        mime = mimetypes.guess_type(caminho_audio)[0] or "application/octet-stream"

        try:
            with open(caminho_audio, "rb") as f:
                resp = requests.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    files={"file": (f"audio{extensao}", f, mime)},
                    data={"model": GROQ_MODEL, "language": "pt",
                          "response_format": "verbose_json"},
                    timeout=90,
                )
        except requests.Timeout:
            # POST may have been accepted by the provider. Never replay silently.
            BREAKER.trip(BREAKER_SCOPE, "UNCERTAIN")
            return jsonify({"erro": "resposta incerta", "categoria": "UNCERTAIN"}), 504
        except requests.RequestException:
            BREAKER.trip(BREAKER_SCOPE, "UNCERTAIN")
            return jsonify({"erro": "conexao incerta", "categoria": "UNCERTAIN"}), 502

        if resp.status_code != 200:
            if resp.status_code == 402:
                category = "PAYMENT_REQUIRED"
            elif resp.status_code == 429:
                category = "RATE_LIMIT"
            elif resp.status_code >= 500:
                category = "UPSTREAM_ERROR"
            else:
                category = "REQUEST_REJECTED"
            BREAKER.trip(BREAKER_SCOPE, category,
                         resp.headers.get("Retry-After"))
            return jsonify({"erro": "groq recusou solicitação",
                            "categoria": category}), 503

        try:
            result = normalize_transcription(resp.json())
        except (ValueError, TypeError):
            BREAKER.trip(BREAKER_SCOPE, "UPSTREAM_ERROR")
            return jsonify({"erro": "resposta invalida da groq"}), 502
        BREAKER.success(BREAKER_SCOPE)
        return jsonify(result)


@app.route("/")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
