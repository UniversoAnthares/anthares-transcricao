# Executor B — Groq STT, circuit breaker e Batch (R07.15)

Escopo: itens 27 (AI-01, inventário parcial), 28 (AI-04), 29 (AI-02), 30 (AI-03).
Revisão: 24/10/2026. **Branch de revisão, não implantada em produção.**

## Mudanças implementadas

- app.py reaproveita o consumidor Groq existente. Solicita verbose_json, entrega texto e segmentos com tempos normalizados. Mantém o campo legado texto.
- groq_resilience.py persiste um circuito por escopo em SQLite local. Erro 429 respeita Retry-After; 402 bloqueia até conciliação autorizada; timeout/erro de conexão no POST mantém UNCERTAIN até recibo e confirmação humana. 5xx recebe cooldown limitado.
- groq_batch_ops.py prepara e valida JSONL determinístico, IDs únicos, endpoints/modelos explícitos, hash SHA-256 e limite de 50.000 registros/200MB. O utilitário não transmite ou submete requisições pagas.
- Testes Windows reais: py -3 -m unittest discover -p 'test_groq*.py' -v retornou 8/8 OK em cópia isolada, compilação Python OK.

## Restrições / rollout

1. Circuit SQLite só coordena processos no mesmo host. Em múltiplas réplicas, adaptar ao ledger canônico e certificar fencing antes de habilitar fallback.
2. Circuito UNCERTAIN exige prova externa e reconciliação autorizada antes de desbloquear.
3. O serviço Groq já exige GROQ_API_KEY, mas esta revisão não atesta sua existência no deploy.
4. Antes de STT real, verificar credenciais, autenticação do proxy, quota, privacidade da amostra, autorização de envio e custo. Registrar WER e tempos medidos. Nenhum áudio foi enviado.
5. Antes de Batch real, verificar elegibilidade, orçamento, retenção até 30 dias e SLA, depois upload, batch, polling, download, SHA e reconciliação. Nenhum job submetido.
6. Não ativar fallback independente sem consentimento de privacidade, credencial elegível e orçamento. A branch de implementação ainda requer revisão/promoção.

## Referências oficiais consultadas em 24/10/2026

https://console.groq.com/docs/speech-to-text — modelos, timestamps, limites de 25MB (free) e 100MB (dev), cobrança mínima de 10s, preços indicativos US$0,111/h (v3) e US$0,04/h (turbo).
https://console.groq.com/docs/batch — desconto referencial de 50%, janela de 24h a 7 dias e retenção de até 30 dias.
https://console.groq.com/docs/rate-limits — limites RPM/TPM/ASH/ASD por organização.

## Rollback

Reverter o PR antes da promoção; o checkout produtivo e os publicadores ficaram inalterados. Preservar circuitos e recibos UNCERTAIN até conciliação.
