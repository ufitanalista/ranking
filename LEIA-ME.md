# Ranking de consultores na nuvem

Post "RANKING CONSULTORES" da Copa UFit no WhatsApp a cada 30 min (8h às 22h), sem depender do PC.

- `rodar.sh`: uma rodada (fechamento de ontem na 1ª do dia, depois o post só se o top 15 mudou).
- `.github/workflows/ranking.yml`: roda no GitHub Actions quando o cron-job.org chama (`workflow_dispatch`).
- `ranking/` e `whatsapp/`: cópias de `ufit-data` e `ufit-whatsapp`. Para atualizar: `python publicar.py --enviar`.
- Estado entre rodadas (histórico do dia, sessão do portal e do WhatsApp): cache do GitHub, criptografado (AES-256-GCM, `CHAVE_ESTADO`).
- Secrets: `PORTAL_CRED`, `CHAVE_ESTADO`, `GRUPO_RANKING`, `GRUPO_AVISOS` (gravar com `python ferramentas/gravar_segredos.py`).
- WhatsApp da nuvem desconectado: `python ferramentas/preparar_estado.py` (novo QR), `python publicar.py --enviar` e apagar os caches `estado-*` em Actions > Caches.
