"""Lê as credenciais das APIs. Nenhum segredo fica gravado nesta pasta."""
import json
import os
from pathlib import Path

CLAUDE = Path.home() / ".claude"


def evo():
    """EVO ABC: arquivo fora do OneDrive (C:\\Users\\<voce>\\.claude\\evo-api-credentials.json)."""
    arq = Path(os.environ.get("UFIT_EVO_CRED") or CLAUDE / "evo-api-credentials.json")  # na nuvem vem dos Secrets
    c = json.loads(arq.read_text(encoding="utf-8"))
    return c["baseUrl"].rstrip("/"), dict(c["headers"])


def evotalks_token():
    """EvoTalks: variável EVOTALKS_MCP_TOKEN, ou o mesmo token do MCP 'omni' do Claude Code."""
    token = os.environ.get("EVOTALKS_MCP_TOKEN")
    if token:
        return token if token.startswith("Bearer ") else "Bearer " + token
    cfg = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    for pasta, projeto in cfg.get("projects", {}).items():
        omni = projeto.get("mcpServers", {}).get("omni")
        if omni:
            return omni["headers"]["Authorization"]
    raise RuntimeError("Token do EvoTalks não encontrado (defina EVOTALKS_MCP_TOKEN).")
