# AI-02 / item 29 — Groq STT, homologação delimitada

Data: 2026-10-25 (America/Campo_Grande). Owner: chatgpt-ops. Job: r07-item29-ai02-20261025.

Fonte de governança: manifesto GitHub main `2e28d54043d6bad1`; preflight local aprovado `f6fc9ca59a96e451`. Divergência de versões preservada. Fonte de critérios: checklist R07, posição fixa 29 (AI-02), antigo item 31.

## Executado
- Serviço canônico inspecionado: `UniversoAnthares/anthares-transcricao`, `app.py` usa Groq Whisper e `GROQ_API_KEY`; branch de outro executor PR #6 mantém circuit breaker e timestamps, sem merge/deploy.
- Amostra WAV 16-bit mono em português gerada por sintetizador local do Windows, arquivo privado de QA com 435.556 bytes, digest `f9bb3514868366b39cdf220bdf2d8306edd5ff7c2b34ba91f386ec978634d331`.
- Verificador isolado com API Groq de transcrição `whisper-large-v3-turbo`, `verbose_json`, um POST explícito e nenhum replay automático; compara texto com referência por WER, verifica intervalos de timestamps, confere limites de mídia, estima custo, captura headers de quota e separa estado de retenção da conta.
- Quatro testes locais `py -3.12 -m unittest discover -s ... -p test_ai02_*.py -v`: 4/4 PASS. Testes prévios do Executor B em diretório independente: 8/8 PASS.
- Execução local `--audio ... --reference ...` sem `--live` retornou `NO_LIVE_CALL`. Execução com `--live` retornou `BLOCKED_NO_AUTHORIZED_KEY`; nenhum áudio foi enviado à Groq. Não houve consumo de API Groq.
- Consulta de projeto Vercel por 'transcri' e 'groq': zero projeto correspondente na conexão Vercel utilizada; isso não comprova ausência de outros serviços.
- Uma tentativa de operação remota via SSH foi bloqueada pela camada de segurança da ferramenta, sem efeitos declarados. Esse caminho não foi repetido por outro controle remoto.

## Critérios ainda sem prova
1. Obter execução autenticada diretamente em ambiente Groq já autorizado e comprovar identidade do projeto, modelo e limites efetivos sem expor a credencial. O Windows SYSTEM consultado não apresentou `GROQ_API_KEY` (processo/usuário/máquina).
2. Enviar uma única amostra autorizada, medir latência e WER reais, verificar timestamps contra marcação temporal de referência (inspeção de monotonicidade não prova precisão absoluta).
3. Conferir quota observada em resposta e uso contabilizado no projeto, orçamento compartilhado e política de retenção/ZDR da organização.
4. Decidir integração com consumidor existente apenas após gate, revisão da PR #6 e testes de rollback. Preservar a transcrição local e o caminho legado.

## Referências
- Serviço Groq: https://console.groq.com/docs/speech-to-text
- Limites: https://console.groq.com/docs/rate-limits
- Retenção: https://console.groq.com/docs/your-data
- Implementação concorrente: https://github.com/UniversoAnthares/anthares-transcricao/pull/6
- Checklist canônico: https://docs.google.com/document/d/1SkjpRPJYLe9n_9SDOA4s-RibN8Pb_hm6-ukS6pbV7aQ/edit

**Estado AI-02: PARCIAL (QA offline implantado em branch).** Nenhum resultado foi promovido a transcrição Groq real, uso em produção ou homologação integral.
