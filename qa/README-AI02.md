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

## TESTE REAL APROVADO EM 25/10/2026 — AI-02 / item 29

**Transcrição autenticada comprovada:** principal Windows DESKTOP-FTDK0HP\Lucas tem GROQ_API_KEY no próprio ambiente; SYSTEM não tem. A chave não foi exibida. GET /models autenticado HTTP 200, com ambos modelos Whisper disponíveis. WAV pt-BR estritamente sintético, 435.556 bytes, SHA256 f9bb3514868366b39cdf220bdf2d8306edd5ff7c2b34ba91f386ec978634d331.

**Diagnóstico e correção:** a consulta GET /models com User-Agent padrão de Python urllib retornou HTTP 403; a mesma consulta com User-Agent explícito HTTP 200. Primeira requisição POST STT antes da correção HTTP 403, sem replay. Corrigido em qa/ai02_groq_stt_acceptance.py para enviar User-Agent anthares-ai02-acceptance/1.0. Acrescentado teste mockado para este cabeçalho: 5/5 unittest PASS. Hash SHA256 do script local corrigido f882a71771fbd4aea9cfdfafff48b377390999d8b5cf1fffbf25c2bf3e6b6829; testes 6624baa28915691fb767f5ff46d3c2c2b6b40926d00d42536ec8c2a4310db000.

**Primeira transcrição real (depois da correção):** model whisper-large-v3-turbo; duração 9,876 s; WER 0,00000 contra fala sintetizada; latência 0,875 s; 2 segmentos, sequenciais e em limites válidos; quota x-ratelimit-limit-requests 2000, remaining-requests 1999, reset-requests 43.2s; status PASS_LIVE_REQUIRES_ACCOUNT_ZDR_CHECK.

**Segunda execução real dedicada ao alinhamento:** latência 1,141 s, WER 0,00000. Texto: A literatura brasileira possui uma longa história. O escritor observa as palavras e organiza suas frases. Segmentos Groq: [0,00;3,36] e [4,44;8,80] segundos. Análise independente da energia RMS do WAV com quadros de 10 ms: começo de fala 0,11 s; silêncio [3,53;4,47] s; final de fala 8,97 s. Desvios aproximados dos quatro limites: 0,11, 0,17, 0,03, 0,17 s, máximo 0,17 s. Essa referência acústica NÃO equivale à anotação fonética humana. Requisição: req_01m5tgrg70esabkhny7ebdvejd.

**Custo e retenção:** preço público Groq Turbo US$ 0,04/h com mínimo faturável 10 s, estimativa US$ 0,0001111 por inferência; não é despesa contabilizada nem auditoria de fatura. Quota de requisições efetivamente recebida em headers, mas plano, limites de áudio, ZDR e settings da organização não auditados. Política oficial https://console.groq.com/docs/your-data: entradas/saídas de inferência não retidas por padrão, exceto logs operacionais/abuso até 30 dias; ZDR opcional. Nunca modificar ZDR sem coordenação com AI-03 Batch. A mídia usada não contém dados pessoais.

**Decisão de aceite:** HOMOLOGAÇÃO TÉCNICA STT APROVADA PARA AMOSTRA SINTÉTICA. Ativação como fallback em produção ainda condicionada a AI-01, SEC-02, governança de dados, validação com mídia real autorizada, revisão do PR #6, integração e rollback comprovados. Não declarar fallback implantado. Nenhuma alteração produtiva, merge, deploy, publicação ou alteração dos demais publicadores.

## ACEITE AUTÔNOMO FINAL — 26/10/2026 — GROQ FREE E DATA CONTROLS

Fonte: captura enviada pelo titular na conversa, complementada por leitura somente de abas GroqCloud já abertas e autenticadas em Personal / Default Project. Nenhum toggle foi alterado; não foi capturada, persistida ou divulgada credencial.

**ZDR da organização:** Global ZDR = Disabled; Inference APIs ZDR = Disabled; Batch (data storage required) = On; Fine-tuning & LoRA Inference = On. O painel avisa que dados de inferência poderão ser armazenados por até 30 dias para confiabilidade e conformidade. A documentação oficial https://console.groq.com/docs/your-data esclarece que entradas/saídas não são retidas por padrão, exceto eventos de investigação de abuso/reliability (até 30 dias), e que metadados de uso são mantidos. O status ZDR foi identificado e aceito para a **amostra sintética, sem dados pessoais**, não para envio indiscriminado de mídia privada. Global ZDR não deve ser ativado sem coordenação, porque desativa serviços que dependem de armazenamento.

**Plano / custo:** leitura autenticada de GroqCloud Billing / Plans mostrou Free = Current Plan, US$0; Developer = pay-as-you-go, não é o plano atual. Isso fundamenta que a operação AI-02 foi realizada na franquia Free sem habilitar faturamento Developer; o custo teórico da tarifa pública Whisper Turbo era US$0,0001111 por requisição (10 s mínimos), sem fatura ou débito contábil comprovado. A confirmação de consumo por evento no painel Usage continua opcional para auditoria de faturamento, não requisito do teste STT. Batch permanece INDISPONÍVEL nesta conta para AI-03: consulta autenticada GET /batches recebeu HTTP403 code not_available_for_plan, embora o controle 'Batch On' esteja habilitado. Não modificar planos nem presumir disponibilidade Batch.

**Critérios do item fixo 29 AI-02 (pacote autônomo):** transcrição Groq real em áudio autorizado (sintético), duas requisições bem-sucedidas, modelo Whisper Large v3 Turbo, WER=0 sobre fala conhecida, 2 segmentos e desvio acústico aproximado máximo 0,17 s, latências 0,875/1,141 s, quota observada HTTP x-ratelimit-limit-requests=2000/remaining=1999, plano Free e política de retenção da conta verificados. Status do pacote de TESTE: **CONCLUÍDO** em 26/10/2026. Recomendável testar mídia natural de produção em projeto separado quando for autorizado, pois uma amostra TTS não valida robustez ampla.

**Fora do escopo do aceite:** criar ou promover Groq como fallback automático produtivo; isso dependerá de revisão do PR #6, AI-01/SEC-02, mídia permitida, limite de 25 MB para Free, isolamento, regras de privacidade, roteamento, circuito, rollback e prova real de continuidade. Nenhuma alteração em serviço/filas/publicadores/credenciais nesta rodada.

**Documentação canônica:** https://docs.google.com/document/d/1SkjpRPJYLe9n_9SDOA4s-RibN8Pb_hm6-ukS6pbV7aQ/edit — checkpoint AI02-ZDR-20261026. Fonte GitHub governança versão 2e28d54043d6bad1, preflight local PASS versão f6fc9ca59a96e451, divergência preservada.
