import re
import subprocess
import tempfile
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

def limpar_vtt(caminho):
    with open(caminho, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    partes = []
    vistos = set()
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if linha.startswith('WEBVTT'):
            continue
        if '-->' in linha:
            continue
        if re.match(r'^\d+$', linha):
            continue
        linha = re.sub(r'<[^>]+>', '', linha)
        if linha not in vistos:
            vistos.add(linha)
            partes.append(linha)

    return ' '.join(partes)


@app.route('/transcricao')
def transcricao():
    video_id = request.args.get('v', '').strip()
    if not video_id or not re.match(r'^[\w-]{11}$', video_id):
        return jsonify({'erro': 'video_id invalido'}), 400

    url = f'https://www.youtube.com/watch?v={video_id}'

    with tempfile.TemporaryDirectory() as tmp:
        saida = os.path.join(tmp, 'legenda')
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--sub-lang', 'pt,pt-BR,pt-PT',
            '--sub-format', 'vtt',
            '--cookies', 'cookies.txt',
            '-o', saida,
            url,
        ]
        try:
            resultado = subprocess.run(cmd, capture_output=True, timeout=60, check=False, text=True)
        except subprocess.TimeoutExpired:
            return jsonify({'erro': 'timeout'}), 504
        arquivos = [f for f in os.listdir(tmp) if f.endswith('.vtt')]
        if not arquivos:
            return jsonify({'erro': 'sem legenda', 'stderr': resultado.stderr[-1500:], 'stdout': resultado.stdout[-500:]}), 404
            
        arquivos = [f for f in os.listdir(tmp) if f.endswith('.vtt')]
        if not arquivos:
            return jsonify({'erro': 'sem legenda'}), 404

        texto = limpar_vtt(os.path.join(tmp, arquivos[0]))
        if not texto:
            return jsonify({'erro': 'legenda vazia'}), 404

        return jsonify({'texto': texto})


@app.route('/')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
