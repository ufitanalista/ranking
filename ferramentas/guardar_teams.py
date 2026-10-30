"""Guarda o link do Workflows do Teams (copiado com Ctrl+C) em .claude\\ufit-ranking-nuvem.json e grava os Secrets.
    python ferramentas/guardar_teams.py
Não mostra o link na tela. Depois disso, as vendas (dia e mês) vão só para o Teams.
"""
import json, os, subprocess, sys
from pathlib import Path

link = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                      capture_output=True, text=True).stdout.strip()
if not link.startswith("https://") or " " in link:
    sys.exit("Não achei um link na área de transferência. Copie o link do Workflows (Ctrl+C) e rode de novo.")

arq = Path.home() / ".claude" / "ufit-ranking-nuvem.json"
nuvem = json.loads(arq.read_text(encoding="utf-8"))
nuvem["teams_vendas"] = link
arq.write_text(json.dumps(nuvem, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Link do Teams guardado ({link.split('/')[2]}). Gravando os Secrets...")
subprocess.run([sys.executable, str(Path(__file__).with_name("gravar_segredos.py"))], check=True)
