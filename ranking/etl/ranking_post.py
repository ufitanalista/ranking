"""Post "RANKING CONSULTORES" (top 15 do dia) no formato do roteiro do grupo de vendas.

Regras fixas do roteiro: nunca mostrar valor nem quantidade de planos, sem travessão,
sem "Bora pra cima", sem "a gente"/"vendemos"/"gestor(a)". O texto sai em formato
de WhatsApp (*negrito*).
"""
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

TOP = 15
# Gênero de cada consultor, marcado pelo usuário (F/M): só para "isolado/isolada" nos empates.
# Quem não está marcado sai com "sem empate" (nunca adivinhar pelo nome).
GENEROS = Path(__file__).parent.parent / "consultores_genero.csv"
LITORAL = {"Balneário Centro", "Alto São Bento", "Córrego Grande", "Jardim Atlântico", "Jardim Dourado",
           "Morretes", "Pagani", "Pedra Branca", "Ponte do Imaruim", "Tijucas", "Roosevelt"}
NORTE = {"Salto", "Brusque", "Canoinhas", "Gaspar", "Indaial", "São João", "Jaraguá do Sul",
         "São Domingos", "Rio Negro", "Timbó", "CT Santa Terezinha",
         "São Bento do Sul", "Pomerode"}  # as duas entraram no Norte em 26/10/2026, igual ao post do CEO
FORA_DO_RANKING = {"São Bento do Sul": "2026-10-29"}  # unidade: a partir de qual dia (AAAA-MM-DD) sai do ranking
UNIDADE_NOME = {"CT Pedra Branca": "Pedra Branca"}
REGIAO = {"L": ("🌊", "Litoral (Yuna + Berg)"), "N": ("🏔️", "Norte (Rudinei + Antunes)")}
# Nome curto fixo quando a regra (primeiro + segundo nome) não dá o nome que o grupo usa
APELIDOS = {"JESSICA ADRIANE DOMASK": "Jessica Domask"}
PARTICULAS = {"DA", "DE", "DO", "DAS", "DOS", "E"}
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _sem_acento(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def _generos():
    if not GENEROS.exists():
        return {}
    with open(GENEROS, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.reader(f, delimiter=";"))[1:]
    return {_sem_acento(l[0].strip()): l[2].strip().upper() for l in linhas
            if len(l) >= 3 and l[2].strip().upper() in ("F", "M")}


def unidade_curta(unit_name):
    u = re.sub(r"^UFit\s+", "", unit_name.strip())
    u = re.sub(r"^Premium\s+", "", u)
    return UNIDADE_NOME.get(u, u)


def regiao(unidade):
    return "L" if unidade in LITORAL else "N" if unidade in NORTE else None


COMPOSTOS = {"ANA", "MARIA", "JOAO", "JOSE", "LUIZ", "LUIS"}  # "Ana Paula", "João Victor"...


def _palavras(nome):
    p = re.sub(r"\(.*?\)", " ", nome).split()
    if len(p) > 1 and _sem_acento(p[0]) in COMPOSTOS and p[1].upper() not in PARTICULAS:
        p = [f"{p[0]} {p[1]}"] + p[2:]
    return p


def nomes_curtos(nomes):
    """Primeiro nome; quem divide o primeiro nome com outra pessoa do dia leva o segundo também."""
    primeiro = Counter(_sem_acento(_palavras(n)[0]) for n in nomes if _palavras(n))
    saida = {}
    for n in nomes:
        p = _palavras(n)
        if not p:
            saida[n] = n
            continue
        if _sem_acento(" ".join(p)) in APELIDOS:
            saida[n] = APELIDOS[_sem_acento(" ".join(p))]
            continue
        curto = [p[0]]
        if primeiro[_sem_acento(p[0])] > 1:
            resto = [w for w in p[1:] if w.upper() not in PARTICULAS]
            curto += resto[:1]
        saida[n] = " ".join(w.capitalize() for w in " ".join(curto).split())
    return saida


def montar_top(dados):
    """Lista do dia na ordem do app (mais planos, depois maior valor), sem as unidades fora do ranking.
    No top só entra quem já tem plano: com menos de 15, o post mostra só esses."""
    dia = dados.get("date") or ""
    lista = [c for c in dados["consultores"] if dia < FORA_DO_RANKING.get(unidade_curta(c["unitName"]), "9999")]
    lista.sort(key=lambda c: (-c["totalPlans"], -c["totalValue"]))
    curtos = nomes_curtos([c["name"] for c in lista])
    generos = _generos()
    top = []
    for i, c in enumerate([c for c in lista if c["totalPlans"] > 0][:TOP], 1):
        u = unidade_curta(c["unitName"])
        top.append({"id": c["id"], "nome": curtos[c["name"]], "genero": generos.get(_sem_acento(c["name"].strip())),
                    "unidade": u, "regiao": regiao(u),
                    "pos": i, "planos": c["totalPlans"], "ativo": c.get("ativo", True)})
    planos_todos = {c["id"]: c["totalPlans"] for c in lista}
    nomes_todos = {c["id"]: f'{curtos[c["name"]]} ({unidade_curta(c["unitName"])})' for c in lista}
    return top, planos_todos, nomes_todos


def _assinatura(top):
    """O que aparece no post: a ordem e quem está empatado com o próximo."""
    return [(c["id"], i + 1 < len(top) and top[i + 1]["planos"] == c["planos"]) for i, c in enumerate(top)]


def mudou(dados, estado):
    atualizacoes = estado.get("atualizacoes", [])
    if not atualizacoes:
        return True
    top, _, _ = montar_top(dados)
    return _assinatura(top) != _assinatura(atualizacoes[-1]["top"])


def _lista(nomes):
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def _detalhe(ant, nova, voltou):
    if ant is None:
        if nova == 1:
            return "voltou ao top 15 direto na ponta" if voltou else "entrou direto na ponta"
        if nova <= 3:
            return "voltou ao top 15 direto no pódio" if voltou else "entrou direto no pódio"
        return "voltou ao top 15" if voltou else ""
    if nova == ant:
        return ""
    d = abs(ant - nova)
    if nova < ant:
        partes = [f"subiu {d}, de {ant}º" if d >= 3 else f"de {ant}º"]
        if nova == 1:
            partes.append("assumiu a ponta")
        elif nova <= 3 < ant:
            partes.append("entrou no pódio")
        elif nova <= 10 < ant:
            partes.append("entrou no top 10")
    else:
        partes = [f"caiu {d}, de {ant}º" if d >= 3 else f"de {ant}º"]
        if ant == 1:
            partes.append("perdeu a ponta")
        elif ant <= 3 < nova:
            partes.append("saiu do pódio")
        elif ant <= 10 < nova:
            partes.append("saiu do top 10")
    return ", ".join(partes)


def _marcador(ant, nova):
    if ant is None:
        return "🆕"
    return "🟢⬆️" if nova < ant else "🔴⬇️" if nova > ant else "⚪️="


def _empates(top):
    linhas, i = [], 0
    while i < len(top):
        j = i
        while j + 1 < len(top) and top[j + 1]["planos"] == top[i]["planos"]:
            j += 1
        grupo = top[i:j + 1]
        if len(grupo) > 1:
            de, ate = grupo[0]["pos"], grupo[-1]["pos"]
            faixa = f"{de}º e {ate}º" if len(grupo) == 2 else f"{de}º ao {ate}º"
            linhas.append(f"{faixa} empatados: {_lista([c['nome'] for c in grupo])}")
        else:
            c = grupo[0]
            onde = "na ponta" if c["pos"] == 1 else f"no {c['pos']}º"
            g = c.get("genero")
            linhas.append(f"{c['nome']} {'isolada' if g == 'F' else 'isolado'} {onde}" if g
                          else f"{c['nome']} {onde}, sem empate")
        i = j + 1
    return linhas


def _regioes(top):
    n = len(top)
    cont = Counter(c["regiao"] for c in top if c["regiao"])
    lider = top[0]["regiao"] if top else None
    linhas = []
    for r in sorted(REGIAO, key=lambda r: (-cont[r], r != "L")):
        emoji, nome = REGIAO[r]
        pct = int(cont[r] * 100 / n + 0.5) if n else 0
        onde = f"no top {TOP}" if n >= TOP else "no ranking"
        linhas.append(f"{emoji} {nome}: {cont[r]} {onde} ({pct}%)" + (", com o 1º lugar" if r == lider else ""))
    return linhas


def _unidades_fortes(top):
    cont = Counter(c["unidade"] for c in top)
    return [(u, k) for u, k in cont.most_common() if k >= 2]


def gerar(dados, estado, agora, fechamento=False):
    """Devolve (post, observacoes, estado_novo). `estado` é o histórico do dia (vazio na 1ª atualização)."""
    top, planos_todos, nomes_todos = montar_top(dados)
    atualizacoes = estado.get("atualizacoes", [])
    anterior = atualizacoes[-1] if atualizacoes else None
    primeira = anterior is None and not fechamento
    pos_ant = {c["id"]: c["pos"] for c in anterior["top"]} if anterior else {}
    ja_esteve = set(estado.get("ja_esteve", []))

    data = agora if not fechamento else None
    if fechamento:
        cab = f"🏆 *RANKING CONSULTORES* (fechamento final do dia {dados['date'][8:10]})"
    elif primeira:
        cab = f"🏆 *RANKING CONSULTORES* ({DIAS[data.weekday()]}, {data:%d/%m} · 1ª atualização, {data:%Hh%M})"
    else:
        cab = f"🏆 *RANKING CONSULTORES* ({DIAS[data.weekday()]}, {data:%d/%m} · atualização {data:%Hh%M})"

    linhas, maior_subida, entraram_podio, entraram = [cab, ""], None, [], []
    for c in top:
        ant = pos_ant.get(c["id"])
        if primeira:
            marc, det = "🆕", ""
        else:
            marc, det = _marcador(ant, c["pos"]), _detalhe(ant, c["pos"], c["id"] in ja_esteve)
        if ant is not None and ant - c["pos"] >= 3 and (not maior_subida or ant - c["pos"] > maior_subida[1]):
            maior_subida = (c["nome"], ant - c["pos"])
        if not primeira and c["pos"] <= 3 and (ant is None or ant > 3):
            entraram_podio.append(c["nome"])
        if not primeira and ant is None:
            entraram.append(c["nome"])
        emoji = REGIAO[c["regiao"]][0] if c["regiao"] else "❓"
        linha = f"{marc} {c['pos']}º {c['nome']} ({c['unidade']}) {emoji}"
        if det:
            linha += f" ({det})"
        linhas.append(linha)

    onde = f"top {TOP}" if len(top) >= TOP else "ranking"  # com menos de 15 nomes não existe "top 15"
    if not primeira:
        ids_agora = {c["id"] for c in top}
        sairam = [f"{c['nome']} ({c['unidade']})" for c in anterior["top"] if c["id"] not in ids_agora] if anterior else []
        linhas.append("")
        if sairam:
            linhas.append(f"❌ Saíram do top {TOP}: {_lista(sairam)}")
        elif not entraram:
            linhas.append(f"Ninguém entrou nem saiu do {onde} nessa rodada.")
        else:
            linhas.append(f"Ninguém saiu do {onde} nessa rodada.")

    linhas += ["", "🤝 *Empates:*"] + _empates(top) + [""] + _regioes(top) + [""]

    lider = top[0]["nome"] if top else None
    lider_ant = anterior["top"][0]["nome"] if anterior and anterior["top"] else None
    fortes = _unidades_fortes(top)
    if fechamento:
        linhas.append("*Resumo do dia:*")
        linhas += _resumo_dia(atualizacoes + [{"top": top, "maior_subida": maior_subida}], fortes)
    elif primeira:
        frases = [f"{lider} abre o dia na ponta."] if lider else []
        if fortes:
            frases.append(_lista([f"{u} com {k} nomes" for u, k in fortes[:2]]) + f" no {onde}.")
        if len(top) < TOP:
            frases.append("Quem fechar 1 plano já entra no ranking.")
        linhas.append("Destaques da abertura: " + " ".join(frases))
    else:
        frases = []
        if lider and lider_ant and lider != lider_ant:
            frases.append(f"{lider} assumiu a ponta no lugar de {lider_ant}.")
        elif lider:
            frases.append(f"{lider} segue na ponta.")
        if maior_subida:
            frases.append(f"{maior_subida[0]} foi quem mais subiu ({maior_subida[1]} posições).")
        podio = [n for n in entraram_podio if n != lider]
        if podio:
            frases.append(f"{_lista(podio)} {'entrou' if len(podio) == 1 else 'entraram'} no pódio.")
        if entraram and len(frases) < 4:
            frases.append(f"{'Entrou' if len(entraram) == 1 else 'Entraram'} no {onde}: {_lista(entraram)}.")
        if len(frases) < 2 and fortes:
            u, k = fortes[0]
            frases.append(f"{u} tem {k} nomes no {onde}.")
        linhas.append("Destaques da rodada: " + " ".join(frases[:4]))

    post = "\n".join(linhas)

    # Avisos para quem posta (fora do post)
    obs = [f"{c['nome']} ({c['unidade']}) aparece como \"Saiu\" no sistema. Vale conferir se ainda está na equipe."
           for c in top if not c["ativo"]]
    for cid, antes in estado.get("planos", {}).items():
        agora_p = planos_todos.get(cid, 0)
        if agora_p < antes:
            obs.append(f"{nomes_todos.get(cid, cid)} caiu de {antes} para {agora_p} planos desde a última atualização "
                       "(pode ser cancelamento ou estorno).")
    obs += [f"Unidade fora da lista de regiões: {c['unidade']} ({c['nome']})." for c in top if not c["regiao"]]

    novo = {
        "data": dados["date"],
        "atualizacoes": atualizacoes + [{"hora": None if fechamento else f"{agora:%H:%M}", "top": top,
                                         "maior_subida": maior_subida}],
        "ja_esteve": sorted(ja_esteve | {c["id"] for c in top}),
        "planos": {**estado.get("planos", {}), **planos_todos},
    }
    return post, obs, novo


def _resumo_dia(atualizacoes, fortes):
    lideres = [a["top"][0]["nome"] for a in atualizacoes if a["top"]]
    linhas = []
    if lideres:
        mais = Counter(lideres).most_common(1)[0]
        trocas = sum(1 for a, b in zip(lideres, lideres[1:]) if a != b)
        linhas.append(f"{mais[0]} liderou em {mais[1]} de {len(lideres)} atualizações. "
                      f"{lideres[-1]} fechou o dia na ponta.")
        linhas.append("A liderança não trocou de mão." if trocas == 0 else
                      f"A liderança trocou de mão {trocas} {'vez' if trocas == 1 else 'vezes'}.")
    subidas = [a["maior_subida"] for a in atualizacoes if a.get("maior_subida")]
    if subidas:
        nome, d = max(subidas, key=lambda s: s[1])
        linhas.append(f"Maior escalada do dia: {nome}, que subiu {d} posições de uma vez.")
    if fortes:
        linhas.append("Unidades com dois ou mais nomes no top 15: " + _lista([f"{u} ({k})" for u, k in fortes]) + ".")
    return linhas
