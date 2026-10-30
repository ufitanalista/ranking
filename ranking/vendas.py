"""Vendas da rede pelo EVO → mensagens para o grupo LEMBRETES.

Uso:
  python vendas.py hora              vendas de hoje até agora, total e por unidade (de hora em hora)
  python vendas.py mes               vendas do mês dia a dia até ontem (no dia 1º, o mês anterior inteiro)
  python vendas.py hora --nao-salvar teste: não grava o total para a comparação da próxima hora

Regra (igual ao Forecast de vendas): soma de todos os itens das vendas não removidas.
"Vendas novas" = sem débito recorrente automático (idSaleRecurrency vazio); "com recorrente" = tudo.
Grava em dados/vendas/ (ou UFIT_VENDAS_DADOS): a mensagem (vendas_*.txt) e o total da última hora.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from etl.evo import Evo

PASTA = Path(os.environ.get("UFIT_VENDAS_DADOS") or Path(__file__).parent / "dados" / "vendas")
# idBranch do EVO → nome curto (mesmos nomes do ranking de consultores)
UNIDADES = {
    13: "Jardim Dourado", 16: "Salto", 18: "Timbó", 25: "Ponte do Imaruim", 26: "Brusque", 27: "Indaial",
    28: "Córrego Grande", 29: "Morretes", 30: "Pagani", 32: "Jardim Atlântico", 33: "Gaspar", 34: "Tijucas",
    35: "Jaraguá do Sul", 36: "Alto São Bento", 37: "São João", 38: "Rio Negro", 39: "Pedra Branca",
    40: "Canoinhas", 41: "Balneário Camboriú", 42: "São Domingos", 43: "Pomerode", 44: "Roosevelt",
    45: "CT Santa Terezinha", 46: "Bombinhas", 47: "São Bento do Sul", 48: "São Francisco do Sul",
    49: "Cidade Nova", 50: "Exclusive Navegantes", 51: "São João Batista",
}
# Unidades que aparecem sempre no relatório da hora, mesmo sem venda (as outras só quando vendem)
SEM_LISTA_FIXA = {46, 48, 50, 51}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def somar(vendas, chave):
    """{chave(venda): [novas, com recorrente]} das vendas não removidas."""
    soma = defaultdict(lambda: [0.0, 0.0])
    for v in vendas:
        if v.get("removed"):
            continue
        valor = sum(i.get("saleValue") or 0 for i in v.get("saleItens") or [])
        s = soma[chave(v)]
        s[1] += valor
        if not v.get("idSaleRecurrency"):
            s[0] += valor
    return soma


def nome_unidade(id_branch):
    return UNIDADES.get(id_branch, f"Unidade {id_branch}")


NEGRITO, FOGO = 5_000, 10_000  # vendas novas da unidade no dia acima disso: negrito; acima de FOGO: negrito + 🔥


def relatorio_hora(evo, agora, salvar):
    hoje = agora.date()
    por_unidade = somar(evo.vendas(f"{hoje}", f"{hoje}"), lambda v: v.get("idBranch"))
    for b in UNIDADES:
        if b not in SEM_LISTA_FIXA:
            por_unidade[b]  # cria com zero quem ainda não vendeu
    novas = sum(s[0] for s in por_unidade.values())
    total = sum(s[1] for s in por_unidade.values())

    arq_ultima = PASTA / f"ultima_{hoje}.json"
    ultima = json.loads(arq_ultima.read_text(encoding="utf-8")) if arq_ultima.exists() else None
    linhas = [f"💰 *Vendas do dia* ({DIAS[hoje.weekday()]}, {hoje:%d/%m} · {agora:%Hh%M})", "",
              f"Vendas novas: *{brl(novas)}*"]
    if ultima:
        linhas[-1] += f" (+{brl(novas - ultima['novas'])} desde as {ultima['hora']})"
    linhas += ["", "*Por unidade:*"]
    ordem = sorted(por_unidade.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))
    for i, (b, (n, t)) in enumerate(ordem, 1):
        texto = f"{i}º {nome_unidade(b)}: {brl(n)}"
        linhas.append(f"*{texto}* 🔥" if n > FOGO else f"*{texto}*" if n > NEGRITO else texto)

    if salvar:
        arq_ultima.write_text(json.dumps({"hora": f"{agora:%Hh%M}", "novas": novas, "total": total}), encoding="utf-8")
    return "\n".join(linhas), f"vendas_{hoje}_{agora:%Hh%M}.txt"


def relatorio_mes(evo, hoje):
    ontem = hoje - timedelta(days=1)
    inicio = ontem.replace(day=1)  # no dia 1º, "ontem" é o último dia do mês anterior: sai o mês inteiro
    por_dia = somar(evo.vendas(f"{inicio}", f"{ontem}"), lambda v: (v.get("saleDate") or "")[:10])
    dias = [inicio + timedelta(days=k) for k in range((ontem - inicio).days + 1)]
    novas_dia = {d: por_dia.get(f"{d}", (0.0, 0.0))[0] for d in dias}
    # Dia bom/ruim comparado com o mesmo dia da semana no mês (domingo é sempre fraco, não é "dia ruim")
    media_semana = {w: sum(v for d, v in novas_dia.items() if d.weekday() == w) /
                       max(1, sum(1 for d in dias if d.weekday() == w)) for w in range(7)}
    melhores = set(sorted(dias, key=lambda d: -novas_dia[d])[:3])
    linhas = [f"📅 *Vendas de {MESES[inicio.month - 1]}* (até {ontem:%d/%m})", ""]
    for d in dias:
        texto = f"{d:%d} {DIAS[d.weekday()][:3]} - {brl(novas_dia[d])}"
        if d in melhores:
            texto = f"*{texto}* 🔥"
        elif novas_dia[d] < 0.7 * media_semana[d.weekday()]:
            texto += " 🔻"
        linhas.append(texto)
    novas = sum(s[0] for s in por_dia.values())
    linhas += ["", f"Total vendas novas: *{brl(novas)}*", "",
               "🔥 3 melhores dias · 🔻 abaixo de 70% da média do mesmo dia da semana"]
    return "\n".join(linhas), f"vendas_mes_{hoje}.txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tipo", choices=["hora", "mes"])
    ap.add_argument("--nao-salvar", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    agora = datetime.now()
    PASTA.mkdir(parents=True, exist_ok=True)
    evo = Evo()
    if a.tipo == "hora":
        texto, nome = relatorio_hora(evo, agora, not a.nao_salvar)
    else:
        texto, nome = relatorio_mes(evo, agora.date())
    if not a.nao_salvar:
        (PASTA / nome).write_text(texto, encoding="utf-8")
        for velho in PASTA.glob("*"):  # guarda só a última semana
            if velho.stat().st_mtime < (agora - timedelta(days=7)).timestamp():
                velho.unlink()
    print(texto)


if __name__ == "__main__":
    main()
