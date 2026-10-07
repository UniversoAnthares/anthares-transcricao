# Anthares Transcrição

Serviço Flask que baixa o áudio de um vídeo do YouTube e o envia à API de transcrição da Groq (Whisper). O áudio fica apenas em um diretório temporário durante a requisição, que é removido ao final do processamento.

## Requisitos

- Python 3.11 ou compatível
- `yt-dlp` disponível no ambiente
- Uma chave `GROQ_API_KEY` válida

As dependências Python estão em `requirements.txt`. O Dockerfile instala o mesmo conjunto e executa o processo com um usuário sem privilégios.

## Execução local

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export GROQ_API_KEY='sua-chave-aqui'
flask --app app run --host 0.0.0.0 --port 5000
```

Não coloque a chave em arquivos rastreados pelo Git. Em produção, forneça-a pelo mecanismo de segredo do ambiente de hospedagem.

## API

- `GET /` retorna `{"status": "ok"}` para verificação de disponibilidade.
- `GET /transcricao?v=VIDEO_ID` aceita um ID do YouTube com 11 caracteres.
- Em sucesso, a resposta é `{"texto": "..."}`.
- O áudio é limitado a 24 MiB após o download. A chamada pode levar até aproximadamente 210 segundos entre o download e a Groq; o processo web admite até 240 segundos.

Os erros tratados pelo serviço retornam JSON em português e não expõem o conteúdo de respostas externas ou de logs de download. Este serviço não implementa autenticação, autorização ou limitação de taxa; coloque-o atrás de controles apropriados antes de expô-lo publicamente.

## Docker

```bash
docker build -t anthares-transcricao .
docker run --rm -p 5000:5000 -e GROQ_API_KEY='sua-chave-aqui' anthares-transcricao
```

## Testes

Os testes não acessam YouTube nem Groq; as integrações são simuladas localmente:

```bash
python -m unittest discover -s tests -v
```

## Limitações e operação

- O download depende da disponibilidade do YouTube e do executável `yt-dlp`.
- A transcrição depende da disponibilidade e dos limites da API Groq.
- Não há cache, persistência, interface web, logo ou outros ativos de marca neste repositório.
- O endpoint é intencionalmente pequeno e aceita somente IDs do YouTube, não URLs arbitrárias.
