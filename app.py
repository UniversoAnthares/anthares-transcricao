import mimetypes
import os
import re
import subprocess
import tempfile

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3"
MAX_AUDIO_BYTES = 24 * 1024 * 1024


@app.route("/transcricao")
def transcricao():
    video_id = request.args.get("v", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return jsonify({"erro": "video_id invalido"}), 400

    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        return jsonify({"erro": "GROQ_API_KEY nao configurada"}), 503

    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmp:
        saida = os.path.join(tmp, "audio.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--max-filesize", str(MAX_AUDIO_BYTES),
            "-f", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
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
            app.logger.exception("Nao foi possivel iniciar o yt-dlp")
            return jsonify({"erro": "servico de download indisponivel"}), 503

        if resultado.returncode != 0:
            app.logger.warning("yt-dlp falhou: %s", resultado.stderr[-1500:])
            if "max-filesize" in resultado.stderr.lower():
                return jsonify({"erro": "audio grande demais"}), 413
            return jsonify({"erro": "download falhou"}), 502

        arquivos = [
            f for f in os.listdir(tmp)
            if f.startswith("audio.")
            and not f.endswith(".part")
            and os.path.isfile(os.path.join(tmp, f))
        ]
        if not arquivos:
            return jsonify({"erro": "sem audio"}), 404
        if len(arquivos) != 1:
            app.logger.warning("yt-dlp produziu arquivos inesperados: %s", arquivos)
            return jsonify({"erro": "download falhou"}), 502

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
                    headers={"Authorization": f"Bearer {groq_api_key}"},
                    files={"file": (f"audio{extensao}", f, mime)},
                    data={"model": GROQ_MODEL, "language": "pt"},
                    timeout=90,
                )
        except requests.RequestException:
            app.logger.exception("Falha de conexao com a Groq")
            return jsonify({"erro": "falha de conexao com groq"}), 502

        if resp.status_code != 200:
            app.logger.warning("Groq retornou status %s: %s", resp.status_code, resp.text[:500])
            return jsonify({"erro": "groq falhou"}), 502

        try:
            payload = resp.json()
        except ValueError:
            return jsonify({"erro": "resposta invalida da groq"}), 502

        if not isinstance(payload, dict):
            return jsonify({"erro": "resposta invalida da groq"}), 502

        texto = payload.get("text", "")

        if not isinstance(texto, str) or not texto.strip():
            return jsonify({"erro": "transcricao vazia"}), 404

        return jsonify({"texto": texto})


@app.route("/")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
