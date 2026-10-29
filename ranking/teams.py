"""Manda um arquivo de texto (no formato do WhatsApp) para um canal do Teams, pelo webhook do Workflows.
    python teams.py arquivo.txt
O link do webhook vem de TEAMS_VENDAS (na nuvem, Secret do GitHub) ou, no PC, de
.claude\\ufit-ranking-nuvem.json ("teams_vendas"). O link é secreto: nunca mostrar nem gravar em outro lugar.
"""
import json, os, re, sys, urllib.request
from pathlib import Path


def link():
    if os.environ.get("TEAMS_VENDAS"):
        return os.environ["TEAMS_VENDAS"]
    arq = Path.home() / ".claude" / "ufit-ranking-nuvem.json"
    return json.loads(arq.read_text(encoding="utf-8")).get("teams_vendas") or sys.exit("Sem o link do Teams (teams_vendas).")


def cartao(texto):
    # WhatsApp usa *negrito*; o Teams, **negrito**. Uma linha por bloco para o Teams não juntar as linhas.
    corpo, espaco = [], "None"
    for linha in texto.strip().splitlines():
        if not linha.strip():
            espaco = "Medium"
            continue
        corpo.append({"type": "TextBlock", "text": re.sub(r"\*([^*]+)\*", r"**\1**", linha),
                      "wrap": True, "spacing": espaco})
        espaco = "None"
    corpo[0].update(size="Large", weight="Bolder")
    return {"type": "message", "attachments": [{
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {"type": "AdaptiveCard", "version": "1.4", "msteams": {"width": "Full"},
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "body": corpo}}]}


def enviar(arquivo):
    dados = json.dumps(cartao(Path(arquivo).read_text(encoding="utf-8"))).encode("utf-8")
    req = urllib.request.Request(link(), data=dados, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status not in (200, 202):
            sys.exit(f"Erro: Teams respondeu {r.status}")
    print(f"Enviado ao Teams: {Path(arquivo).name}")


if __name__ == "__main__":
    enviar(sys.argv[1])
