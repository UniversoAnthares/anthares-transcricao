# Anthares Transcrição

Serviço Flask que baixa o áudio de um vídeo do YouTube por ID e envia o arquivo ao endpoint de transcrição da Groq. O serviço é uma API de backend; ele **não fornece autenticação, rate limit ou quota próprios**. Em produção, coloque-o atrás de um gateway autenticado e com limites de concorrência/custo.

## Configuração

- `GROQ_API_KEY` — chave da Groq, fornecida somente pelo ambiente de execução; nunca a versione.
- `PORT` — porta HTTP; padrão `5000`.

## API

- `GET /` retorna `{"status":"ok"}`.
- `GET /transcricao?v=<video_id>` aceita um ID YouTube de 11 caracteres.
- O download é limitado a 24 MiB e a 120 segundos antes do envio à Groq.
- Respostas de erro usam a chave `erro` e não devolvem stderr do `yt-dlp`, corpo bruto da Groq ou exceções de rede.

Exemplo:

```bash
GROQ_API_KEY=... python3 app.py
curl 'http://127.0.0.1:5000/transcricao?v=dQw4w9WgXcQ'
```

## Execução

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile app.py
```

O container e o `Procfile` iniciam Gunicorn na porta definida por `PORT`. O fluxo envia o áudio a um terceiro (Groq); operadores devem aplicar a política de privacidade e retenção adequada ao conteúdo processado.

## Segurança

Não grave cookies do YouTube, chaves, tokens, arquivos de sessão ou `.env` no Git. O histórico antigo deste repositório contém um artefato de cookies removido posteriormente; essa credencial deve ser tratada como comprometida, revogada e saneada pelos responsáveis antes de qualquer uso em produção.
