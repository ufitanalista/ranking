"""Portal UFit (ufitcentral.online): login e ranking de vendas da Copa UFit."""
import http.cookiejar
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://ufitcentral.online"
# Login do portal, fora do OneDrive de propósito: {"login": "...", "senha": "..."}
CREDENCIAIS = Path(os.environ.get("UFIT_PORTAL_CRED") or Path.home() / ".claude" / "ufitcentral-credentials.json")
UA = "ufit-ranking/0.1"  # o Cloudflare bloqueia o User-Agent padrão do Python


# Sessão guardada entre rodadas: entrar a cada 30 min derruba o login do usuário no navegador
SESSAO = Path(os.environ.get("UFIT_PORTAL_SESSAO") or Path.home() / ".claude" / "ufitcentral-sessao.txt")


class Portal:
    def __init__(self):
        self.jar = http.cookiejar.LWPCookieJar(str(SESSAO))
        if SESSAO.exists():
            self.jar.load(ignore_discard=True, ignore_expires=True)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def _req(self, caminho, dados=None):
        corpo = urllib.parse.urlencode(dados).encode() if dados is not None else None
        req = urllib.request.Request(BASE + caminho, data=corpo, headers={"User-Agent": UA, "Accept": "application/json"})
        if corpo is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with self.opener.open(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    def entrar(self):
        if (self._req("/api/auth/session") or {}).get("user"):
            return self  # a sessão guardada ainda vale
        if not CREDENCIAIS.exists():
            raise RuntimeError(f"Falta o arquivo de login do portal: {CREDENCIAIS}")
        cred = json.loads(CREDENCIAIS.read_text(encoding="utf-8"))
        if not cred.get("login") or not cred.get("senha"):
            raise RuntimeError(f"Preencha login e senha em {CREDENCIAIS}")
        csrf = self._req("/api/auth/csrf")["csrfToken"]
        r = self._req("/api/auth/callback/credentials", {
            "csrfToken": csrf, "email": cred["login"], "password": cred["senha"],
            "json": "true", "callbackUrl": BASE + "/"})
        if "error" in (r.get("url") or ""):
            raise RuntimeError("O portal recusou o login (confira login e senha)")
        if not (self._req("/api/auth/session") or {}).get("user"):
            raise RuntimeError("Login no portal sem sessão (pode estar pedindo código de verificação)")
        self.jar.save(ignore_discard=True, ignore_expires=True)
        return self

    def ranking_dia(self, data):
        """Ranking de vendas do dia ('AAAA-MM-DD'), o mesmo da aba Ranking Vendas → Dia a dia."""
        return self._req(f"/api/vendas/ranking-vendas?scope=dia&year={data[:4]}&date={data}")
