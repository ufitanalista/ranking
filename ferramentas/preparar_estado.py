"""Monta o estado-inicial.enc: um WhatsApp conectado só para a nuvem + a sessão do portal do PC.
Rodar uma vez (e de novo se o WhatsApp da nuvem for desconectado no celular):
    python ferramentas/preparar_estado.py
Abre um QR code: no celular, WhatsApp > Aparelhos conectados > Conectar aparelho.
Nada fica aberto no disco: a pasta temporária é apagada no fim, só sobra o arquivo criptografado.
"""
import json, os, shutil, subprocess, tarfile, tempfile
from pathlib import Path

CASA = Path.home() / '.claude'
PROJETO = Path(__file__).resolve().parent.parent
WHATSAPP = Path.home() / 'ufit-whatsapp' / 'whatsapp.mjs'   # mesma cópia do PC, com o node_modules instalado

chave = json.loads((CASA / 'ufit-ranking-nuvem.json').read_text(encoding='utf-8'))['chave_estado']
tmp = Path(tempfile.mkdtemp(prefix='ranking-nuvem-'))
try:
    estado = tmp / 'estado'
    (estado / 'ranking').mkdir(parents=True)
    env = dict(os.environ, WA_SESSAO=str(estado / 'whatsapp'))
    subprocess.run(['node', str(WHATSAPP), 'conectar'], env=env, check=True)
    # Mesma sessão do portal do PC: assim a nuvem e o PC não derrubam o login um do outro
    sessao = CASA / 'ufitcentral-sessao.txt'
    if sessao.exists():
        shutil.copy(sessao, estado / 'portal-sessao.txt')
    with tarfile.open(tmp / 'estado.tgz', 'w:gz') as t:
        for p in estado.iterdir():
            t.add(p, arcname=p.name)
    subprocess.run(['node', str(PROJETO / 'ferramentas' / 'cripto.js'), 'cifrar', 'CHAVE_ESTADO',
                    str(tmp / 'estado.tgz'), str(PROJETO / 'estado-inicial.enc')],
                   env=dict(os.environ, CHAVE_ESTADO=chave), check=True)
    print('Pronto: estado-inicial.enc criado. Agora: python publicar.py')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
