#!/usr/bin/env bash
# Uma rodada do ranking na nuvem (GitHub Actions), a mesma lógica do ranking_tarefa.ps1 do PC:
# 1) na 1ª rodada do dia, manda o fechamento de ontem;
# 2) gera o post de agora e manda para GRUPO_RANKING; se o top 15 não mudou, não manda nada.
# Erros e avisos (portal, "Saiu", plano a menos) vão para GRUPO_AVISOS.
# Precisa de: UFIT_RANKING_DADOS, UFIT_PORTAL_CRED, UFIT_PORTAL_SESSAO, WA_SESSAO, GRUPO_RANKING, GRUPO_AVISOS.
set -u
cd "$(dirname "$0")"
SEM_MUDANCA=10
DADOS="$UFIT_RANKING_DADOS"
mkdir -p "$DADOS"

agora=$(date +%H%M)
if [ "${FORCAR:-false}" != "true" ] && { [ "$((10#$agora))" -lt 755 ] || [ "$((10#$agora))" -gt 2210 ]; }; then
  echo "Fora do horário (8h-22h): nada a fazer."
  exit 0
fi

enviar() {  # enviar <arquivo> <grupo>; falhas de criptografia do WhatsApp costumam passar na tentativa seguinte
  local saida codigo
  for tentativa in 1 2 3; do
    node whatsapp/whatsapp.mjs enviar "$1" --para "$2" > /tmp/wa.txt 2>&1; codigo=$?
    saida=$(grep -e "Enviado" -e "Erro" /tmp/wa.txt | tail -2)
    if [ $codigo -eq 0 ]; then echo "WhatsApp: $saida"; return 0; fi
    echo "WhatsApp (tentativa $tentativa): $saida"
    case "$saida" in *conectar*) break ;; esac
    sleep 20
  done
  echo "::error::WhatsApp não enviou $1"
  return 1
}

avisar() {  # avisar <texto>: manda para o grupo de avisos (só funciona se o WhatsApp estiver conectado)
  printf '⚠️ Ranking UFit (nuvem): %s\n' "$1" > /tmp/aviso.txt
  enviar /tmp/aviso.txt "$GRUPO_AVISOS" || true
}

rodar() {  # rodar [argumentos do ranking.py]; devolve o código de saída
  local saida codigo
  saida=$(python3 ranking/ranking.py "$@" 2>&1); codigo=$?
  echo "$saida" | tail -40
  if [ $codigo -ne 0 ] && [ $codigo -ne $SEM_MUDANCA ]; then
    echo "::error::ranking.py $* falhou"
    case "$saida" in
      *login*|*senha*|*portal*|*HTTP*) avisar "não consegui entrar no portal. Detalhe: $(echo "$saida" | tail -1)" ;;
      *) avisar "erro ao gerar o post. Detalhe: $(echo "$saida" | tail -1)" ;;
    esac
  fi
  return $codigo
}

# Período de teste: até 28/10/2026 o ranking vai para o grupo de avisos (LEMBRETES); depois, para o oficial
if [[ "$(date +%F)" < "2026-10-29" ]]; then GRUPO_RANKING="$GRUPO_AVISOS"; echo "Período de teste: post vai para o grupo de avisos."; fi

falhou=0

# 1) Fechamento de ontem, uma vez só
ontem=$(date -d yesterday +%F)
if [ -f "$DADOS/estado_$ontem.json" ] && [ ! -f "$DADOS/post_${ontem}_fechamento.txt" ]; then
  if rodar --fechamento "$ontem"; then
    enviar "$DADOS/post_${ontem}_fechamento.txt" "$GRUPO_RANKING" || falhou=1
  else
    falhou=1
  fi
fi

# 2) Atualização de agora
hoje=$(date +%F)
antes=$(ls "$DADOS" | grep "^post_${hoje}_" | sort)
rodar; codigo=$?
if [ $codigo -eq $SEM_MUDANCA ]; then
  echo "Sem mudanças no top 15: nada enviado."
elif [ $codigo -eq 0 ]; then
  novo=$(comm -13 <(echo "$antes") <(ls "$DADOS" | grep "^post_${hoje}_" | sort) | tail -1)
  if [ -n "$novo" ]; then
    enviar "$DADOS/$novo" "$GRUPO_RANKING" || { falhou=1; avisar "o post $novo não foi enviado."; }
    avisos="$DADOS/${novo/post_/avisos_}"
    [ -f "$avisos" ] && { cat "$avisos"; enviar "$avisos" "$GRUPO_AVISOS" || true; }
  fi
else
  falhou=1
fi

# 3) Vendas pelo EVO para GRUPO_VENDAS (COMERCIAL UFIT; sem ele, o de avisos): o mês na 1ª rodada do dia, o dia nas horas cheias
VENDAS="$UFIT_VENDAS_DADOS"
mkdir -p "$VENDAS"
vendas() {  # vendas hora|mes <começo do nome do arquivo que ele gera>
  local saida
  if saida=$(python3 ranking/vendas.py "$1" 2>&1); then
    enviar "$(ls -t "$VENDAS"/"$2"*.txt | head -1)" "${GRUPO_VENDAS:-$GRUPO_AVISOS}" || falhou=1
  else
    echo "$saida" | tail -5
    echo "::error::vendas.py $1 falhou"
    avisar "não consegui puxar as vendas do EVO ($1). Detalhe: $(echo "$saida" | tail -1)"
    falhou=1
  fi
}
[ -f "$VENDAS/vendas_mes_$hoje.txt" ] || vendas mes "vendas_mes_$hoje"
hora=$(date +%H)
if [ "$((10#$(date +%M)))" -lt 15 ] && ! ls "$VENDAS" | grep -q "^vendas_${hoje}_${hora}h"; then
  vendas hora "vendas_${hoje}_"
fi

# Guarda só os últimos 3 dias (o estado de ontem é o que faz o fechamento)
find "$DADOS" -type f -mtime +3 -delete
exit $falhou
