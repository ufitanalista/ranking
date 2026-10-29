"""EVO ABC (W12): vendas e unidades."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from . import credenciais

PAUSA = 0.22  # limite da API: ~5 chamadas por segundo


class Evo:
    def __init__(self):
        self.base, self.headers = credenciais.evo()
        self.headers.update({"Accept": "application/json", "User-Agent": "ufit-etl/0.1"})

    def get(self, caminho, params=None):
        url = self.base + caminho + ("?" + urllib.parse.urlencode(params) if params else "")
        for tentativa in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=self.headers),
                                            timeout=120) as r:
                    corpo = r.read()
                time.sleep(PAUSA)
                return json.loads(corpo.decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and tentativa < 4:
                    time.sleep(3 * (tentativa + 1))
                    continue
                raise RuntimeError(f"EVO {e.code} em {caminho}: {e.read()[:300]!r}")

    def unidades(self):
        return self.get("/api/v1/configuration")

    def vendas(self, data_ini, data_fim, progresso=None):
        """Todas as vendas da rede no período (datas 'AAAA-MM-DD'), paginando de 100 em 100."""
        skip = 0
        while True:
            pagina = self.get("/api/v2/sales", {"dateSaleStart": data_ini, "dateSaleEnd": data_fim,
                                                "take": 100, "skip": skip})
            yield from pagina
            if progresso:
                progresso(skip + len(pagina))
            if len(pagina) < 100:
                return
            skip += 100
