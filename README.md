# Anthares Transcrição

API Flask para transcrever o áudio de um vídeo do YouTube usando `yt-dlp` e Groq Whisper.

## Configuração

- `GROQ_API_KEY` (obrigatória): chave da API Groq.
- `PORT` (opcional, padrão `5000`).

## Execução local

```bash
pip install -r requirements.txt
export GROQ_API_KEY=...
python app.py
```

Health check: `GET /`

Transcrição: `GET /transcricao?v=VIDEO_ID`

O download é sem playlist e limitado a 24 MiB. O endpoint deve ser publicado atrás de autenticação, rate limit e quota no proxy de produção; ele não deve ser exposto diretamente à internet sem essas proteções.

## Validação

```bash
python -m py_compile app.py
```

A chave nunca deve ser commitada ou incluída em logs.
