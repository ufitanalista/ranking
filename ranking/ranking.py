"""Ranking de consultores do dia → post pronto para o grupo de vendas.

Uso:
  python ranking.py                         atualização de agora (a 1ª do dia começa do zero)
  python ranking.py --fechamento 2026-10-26 fechamento final do dia (rodar na manhã seguinte)
  python ranking.py --arquivo x.json        usa um JSON salvo da API em vez de entrar no portal (teste)
  python ranking.py --nao-salvar            não grava o histórico do dia (teste)

Se o top 15 não mudou (ordem, quem está nele e os empates), não gera post e sai com código 10.
Grava em dados/ranking/: o histórico do dia (estado_AAAA-MM-DD.json) e cada post (post_AAAA-MM-DD_HHhMM.txt).
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from etl import ranking_post
from etl.portal import Portal

PASTA = Path(os.environ.get("UFIT_RANKING_DADOS") or Path(__file__).parent / "dados" / "ranking")  # na nuvem vem do estado guardado
SEM_MUDANCA = 10  # código de saída quando o top 15 não mudou (a tarefa não envia nada)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fechamento", metavar="AAAA-MM-DD")
    ap.add_argument("--arquivo")
    ap.add_argument("--agora", help="hora simulada AAAA-MM-DDTHH:MM (teste)")
    ap.add_argument("--nao-salvar", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    agora = datetime.fromisoformat(a.agora) if a.agora else datetime.now()
    data = a.fechamento or f"{agora:%Y-%m-%d}"
    if a.arquivo:
        dados = json.loads(Path(a.arquivo).read_text(encoding="utf-8"))
    else:
        dados = Portal().entrar().ranking_dia(data)

    PASTA.mkdir(parents=True, exist_ok=True)
    arq_estado = PASTA / f"estado_{data}.json"
    estado = json.loads(arq_estado.read_text(encoding="utf-8")) if arq_estado.exists() else {}
    if not a.fechamento and not ranking_post.mudou(dados, estado):
        print(f"Sem mudanças no top {ranking_post.TOP} desde a última atualização: nada a enviar.")
        sys.exit(SEM_MUDANCA)
    post, obs, novo = ranking_post.gerar(dados, estado, agora, fechamento=bool(a.fechamento))

    if not a.nao_salvar:
        arq_estado.write_text(json.dumps(novo, ensure_ascii=False, indent=1), encoding="utf-8")
        sufixo = "fechamento" if a.fechamento else f"{agora:%Hh%M}"
        (PASTA / f"post_{data}_{sufixo}.txt").write_text(post, encoding="utf-8")
        if obs:
            (PASTA / f"avisos_{data}_{sufixo}.txt").write_text("\n".join(obs), encoding="utf-8")

    print(post)
    if obs:
        print("\n--- Avisos (fora do post) ---")
        print("\n".join(obs))


if __name__ == "__main__":
    main()
