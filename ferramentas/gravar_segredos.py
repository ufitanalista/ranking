"""Grava no cofre do GitHub (Secrets do projeto ranking) o login do portal, a chave e os grupos, sem mostrar nada na tela.
Rodar pelo próprio usuário (uma vez, ou de novo para trocar a senha do portal ou o grupo):
    python ferramentas/gravar_segredos.py
Lê de C:\\Users\\<usuário>\\.claude: ufitcentral-credentials.json, evo-api-credentials.json e ufit-ranking-nuvem.json.
"""
import json, os, subprocess

CASA = os.path.join(os.path.expanduser('~'), '.claude')
GH = os.path.join(os.path.expanduser('~'), '.local', 'gh', 'bin', 'gh.exe')
PROJETO = 'ufitanalista/ranking'


def ler(n):
    with open(os.path.join(CASA, n), encoding='utf-8') as f:
        return f.read()


nuvem = json.loads(ler('ufit-ranking-nuvem.json'))
segredos = {
    'PORTAL_CRED': ler('ufitcentral-credentials.json'),
    'EVO_CRED': ler('evo-api-credentials.json'),
    'CHAVE_ESTADO': nuvem['chave_estado'],
    'GRUPO_RANKING': nuvem['grupo_ranking'],
    'GRUPO_AVISOS': nuvem['grupo_avisos'],
}
for nome, valor in segredos.items():
    subprocess.run([GH, 'secret', 'set', nome, '-R', PROJETO], input=valor.encode('utf-8'), check=True)
subprocess.run([GH, 'secret', 'list', '-R', PROJETO], check=True)
