"""Copia a versão atual do ranking (ufit-data e ufit-whatsapp) para este projeto e, com --enviar, sobe para o GitHub.
    python publicar.py            só copia e mostra o que mudou
    python publicar.py --enviar   copia, confere e envia
O projeto é PÚBLICO: só entra o que o .gitignore libera, e o único dado é o estado-inicial.enc (criptografado).
"""
import shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI.parent / 'ufit-data'
WHATS = Path.home() / 'ufit-whatsapp'
GIT = 'git'

COPIAS = {
    DATA / 'ranking.py': AQUI / 'ranking' / 'ranking.py',
    DATA / 'etl' / 'portal.py': AQUI / 'ranking' / 'etl' / 'portal.py',
    DATA / 'etl' / 'ranking_post.py': AQUI / 'ranking' / 'etl' / 'ranking_post.py',
    WHATS / 'whatsapp.mjs': AQUI / 'whatsapp' / 'whatsapp.mjs',
    WHATS / 'package.json': AQUI / 'whatsapp' / 'package.json',
    WHATS / 'package-lock.json': AQUI / 'whatsapp' / 'package-lock.json',
}
for origem, destino in COPIAS.items():
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(origem, destino)
(AQUI / 'ranking' / 'etl' / '__init__.py').touch()

git = lambda *a: subprocess.run([GIT, '-C', str(AQUI), *a], check=True, capture_output=True, text=True).stdout
git('add', '-A')
arquivos = git('diff', '--cached', '--name-only').split()
print('\n'.join(arquivos) or 'Nada mudou.')

# Trava de segurança: nada de sessão, credencial ou JSON aberto no projeto público
proibidos = [a for a in git('ls-files').split()
             if a.endswith(('.json', '.txt', '.tgz', '.png')) and not a.endswith('package.json') and not a.endswith('package-lock.json')]
if proibidos:
    sys.exit(f'PAREI: arquivos que não podem ir para o projeto público: {proibidos}')

if '--enviar' in sys.argv and arquivos:
    git('commit', '-m', 'Atualiza o ranking')
    git('push', 'origin', 'main')
    print('Enviado.')
