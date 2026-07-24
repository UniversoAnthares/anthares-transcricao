import re
import subprocess
import tempfile
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

@app.route('/transcricao')
def transcricao():
    video_id = request.args.get('v', '').strip()
    if not video_id or not re.match(r'^[\w-]{11}$', video_id):
        return jsonify({'erro': 'video_id invalido'}), 400
    url = f'https://www.youtube.com/watch?v={video_id}'
    with tempfile.TemporaryDirectory() as tmp:
        saida = os.path.join(tmp, 'audio.%(ext)s')
        cmd = [
            'yt-dlp', '-f', 'bestaudio', '--extract-audio',
            '--audio-format', 'mp3', '--audio-quality', '5',
            '-o', saida, url,
        ]
try:
            resultado = subprocess.run(cmd, capture_output=True, timeout=120, check=False, text=True)
        except subprocess.TimeoutExpired:
            return jsonify({'erro': 'timeout'}), 504
        arquivos = [f for f in os.listdir(tmp) if f.endswith('.mp3')]
        if not arquivos:
            return jsonify({'erro': 'sem audio', 'stderr': resultado.stderr[-1500:]}), 404
        caminho_audio = os.path.join(tmp, arquivos[0])
        if os.path.getsize(caminho_audio) > 24 * 1024 * 1024:
            return jsonify({'erro': 'audio grande demais'}), 413
        with open(caminho_audio, 'rb') as f:
            resp = requests.post(
                'https://api.groq.com/openai/v1/audio/transcriptions',
                headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
                files={'file': (arquivos[0], f, 'audio/mpeg')},
                data={'model': 'whisper-large-v3', 'language': 'pt'},
                timeout=90,
            )
        if resp.status_code != 200:
            return jsonify({'erro': 'groq falhou', 'detalhe': resp.text[:500]}), 502
        texto = resp.json().get('text', '')
        if not texto:
            return jsonify({'erro': 'transcricao vazia'}), 404
        return jsonify({'texto': texto})

@app.route('/')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
